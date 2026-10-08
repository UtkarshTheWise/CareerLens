"""Zip apps/extension/dist into apps/web/public/downloads/careerlens-extension.zip for the install page.

Run `pnpm --filter extension build` first (with apps/extension/.env.local holding the production API and
Supabase values), or just `pnpm pack:extension`. Public values only end up in the zip; .env files never do.
The zip is deterministic (fixed timestamps), so repacking an unchanged build changes nothing in git.
"""

import base64
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "apps" / "extension" / "dist"
OUT = ROOT / "apps" / "web" / "public" / "downloads" / "careerlens-extension.zip"
EXPECTED_ID = "bchilaidlnimfdagenlcpoannjomfkil"


def extension_id(public_key_b64: str) -> str:
    digest = hashlib.sha256(base64.b64decode(public_key_b64)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(c, 16)) for c in digest)


def main() -> int:
    manifest_path = DIST / "manifest.json"
    if not manifest_path.is_file():
        print("apps/extension/dist is missing: run `pnpm --filter extension build` first", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ext_id = extension_id(manifest["key"])
    if ext_id != EXPECTED_ID:
        print(f"extension id is {ext_id}, expected {EXPECTED_ID}", file=sys.stderr)
        return 1
    files = sorted(p for p in DIST.rglob("*") if p.is_file())
    bad = [p for p in files if p.name.startswith(".env")]
    if bad:
        print(f"refusing to pack env files: {bad}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(DIST).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    print(f"{OUT.relative_to(ROOT)}: {len(files)} files, {OUT.stat().st_size // 1024} KB, id {ext_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
