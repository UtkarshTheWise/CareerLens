"""Diff the FastAPI app against contracts/openapi.yaml.

    uv run python scripts/check_contract.py                     # everything must match
    uv run python scripts/check_contract.py --only-implemented  # ignore contract paths not routed yet

Checks: paths + methods, operationIds, and for request/response bodies and every contract
schema: property names, required lists, enum values and basic JSON types (walked recursively).
Descriptions, examples, formats and nullability spelling are ignored. Exits 1 on any mismatch.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

CONTRACT_PATH = API_DIR.parent.parent / "contracts" / "openapi.yaml"
METHODS = ("get", "post", "put", "patch", "delete")
JSON = "application/json"
REF_PREFIX = "#/components/"


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_app_spec() -> dict[str, Any]:
    """app.openapi(), plus the schema of every model in app.schemas.api (routed or not)."""
    from pydantic import BaseModel
    from pydantic.json_schema import models_json_schema

    from app.main import app
    from app.schemas import api

    spec = app.openapi()
    models = [
        obj
        for obj in vars(api).values()
        if isinstance(obj, type)
        and obj.__module__ == api.__name__
        and issubclass(obj, BaseModel)
        and obj is not api.ApiModel
    ]
    _, defs = models_json_schema(
        [(m, "validation") for m in models], ref_template="#/components/schemas/{model}"
    )
    schemas = spec.setdefault("components", {}).setdefault("schemas", {})
    for name, schema in defs.get("$defs", {}).items():
        schemas.setdefault(name, schema)
    return spec


class Spec:
    def __init__(self, doc: dict[str, Any]):
        self.doc = doc

    def deref(self, node: dict[str, Any]) -> dict[str, Any]:
        while isinstance(node, dict) and "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith(REF_PREFIX):
                raise ValueError(f"unsupported $ref {ref}")
            target: Any = self.doc
            for part in ref[2:].split("/"):
                target = target[part]
            node = target
        return node

    def resolve(self, schema: dict[str, Any] | None) -> dict[str, Any]:
        """Flatten $ref, allOf and nullable wrappers into one plain schema."""
        if not schema:
            return {}
        schema = self.deref(schema)
        if "allOf" in schema:
            merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
            for part in schema["allOf"]:
                part = self.resolve(part)
                merged["properties"].update(part.get("properties", {}))
                merged["required"] += part.get("required", [])
                if "enum" in part or part.get("type") not in (None, "object"):
                    return part  # allOf used only to attach a description to a $ref
            merged["properties"].update(schema.get("properties", {}))
            merged["required"] += schema.get("required", [])
            return merged
        for key in ("anyOf", "oneOf"):
            if key in schema:
                options = [o for o in schema[key] if self.deref(o).get("type") != "null"]
                return self.resolve(options[0]) if len(options) == 1 else {}
        return schema

    def operations(self) -> dict[tuple[str, str], dict[str, Any]]:
        ops = {}
        for path, item in self.doc.get("paths", {}).items():
            for method in METHODS:
                if method in item:
                    ops[(path, method)] = item[method]
        return ops

    def body_schema(self, container: dict[str, Any] | None) -> dict[str, Any] | None:
        container = self.deref(container or {})
        media = container.get("content", {}).get(JSON)
        return media.get("schema") if media else None


def _type_of(schema: dict[str, Any]) -> str | None:
    if "const" in schema or "enum" in schema:
        return "enum"
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), None)
    if t is None and "properties" in schema:
        t = "object"
    return t


def compare(
    want: dict | None, got: dict | None, contract: Spec, app: Spec, where: str, out: list[str]
) -> None:
    """Append one line to `out` per difference between a contract schema and an app schema."""
    w, g = contract.resolve(want), app.resolve(got)
    wt, gt = _type_of(w), _type_of(g)
    if wt is None or gt is None:  # free-form on one side (e.g. Any): nothing to compare
        return
    if wt != gt:
        out.append(f"{where}: type is {gt}, contract says {wt}")
        return
    if wt == "enum":
        we = sorted(map(str, w.get("enum", [w.get("const")])))
        ge = sorted(map(str, g.get("enum", [g.get("const")])))
        if we != ge:
            out.append(f"{where}: enum is {ge}, contract says {we}")
    elif wt == "array":
        compare(w.get("items"), g.get("items"), contract, app, f"{where}[]", out)
    elif wt == "object":
        wp, gp = w.get("properties", {}), g.get("properties", {})
        if not wp:  # free-form object in the contract (details, ...)
            return
        for name in sorted(set(wp) - set(gp)):
            out.append(f"{where}: missing property '{name}'")
        for name in sorted(set(gp) - set(wp)):
            out.append(f"{where}: extra property '{name}'")
        wr, gr = set(w.get("required", [])), set(g.get("required", []))
        for name in sorted(wr - gr):
            out.append(f"{where}: '{name}' must be required")
        for name in sorted(gr - wr):
            out.append(f"{where}: '{name}' is required but optional in the contract")
        for name in sorted(set(wp) & set(gp)):
            compare(wp[name], gp[name], contract, app, f"{where}.{name}", out)


def check(contract_doc: dict[str, Any], app_doc: dict[str, Any], only_implemented: bool = False) -> list[str]:
    contract, app = Spec(contract_doc), Spec(app_doc)
    out: list[str] = []
    c_ops, a_ops = contract.operations(), app.operations()

    for path, method in sorted(set(c_ops) - set(a_ops)):
        if not only_implemented:
            out.append(f"{method.upper()} {path}: in the contract, not routed")
    for path, method in sorted(set(a_ops) - set(c_ops)):
        out.append(f"{method.upper()} {path}: routed, not in the contract")

    for key in sorted(set(c_ops) & set(a_ops)):
        c_op, a_op = c_ops[key], a_ops[key]
        where = f"{key[1].upper()} {key[0]}"
        if c_op.get("operationId") != a_op.get("operationId"):
            got_id, want_id = a_op.get("operationId"), c_op.get("operationId")
            out.append(f"{where}: operationId is {got_id}, contract says {want_id}")
        c_body = contract.body_schema(c_op.get("requestBody"))
        if c_body is not None:
            compare(
                c_body,
                app.body_schema(a_op.get("requestBody")) or {"type": "null"},
                contract,
                app,
                f"{where} request",
                out,
            )
        for status, c_resp in c_op.get("responses", {}).items():
            if status == "default":
                continue
            a_resp = a_op.get("responses", {}).get(status)
            if a_resp is None:
                if status.startswith("2"):
                    out.append(f"{where}: response {status} not declared")
                continue
            c_schema = contract.body_schema(c_resp)
            if c_schema is not None:
                compare(
                    c_schema,
                    app.body_schema(a_resp) or {"type": "null"},
                    contract,
                    app,
                    f"{where} -> {status}",
                    out,
                )

    a_schemas = app_doc.get("components", {}).get("schemas", {})
    for name, c_schema in sorted(contract_doc.get("components", {}).get("schemas", {}).items()):
        if name not in a_schemas:
            out.append(f"schema {name}: missing in app/schemas/api.py")
        else:
            compare(c_schema, a_schemas[name], contract, app, f"schema {name}", out)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only-implemented", action="store_true", help="ignore unrouted contract paths")
    args = parser.parse_args(argv)

    contract_doc, app_doc = load_contract(), load_app_spec()
    problems = check(contract_doc, app_doc, args.only_implemented)
    routed = len(set(Spec(contract_doc).operations()) & set(Spec(app_doc).operations()))
    total = len(Spec(contract_doc).operations())
    for line in problems:
        print(line)
    print(f"{routed}/{total} contract operations routed; {len(problems)} mismatch(es)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
