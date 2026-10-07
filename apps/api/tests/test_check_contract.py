import copy

from scripts.check_contract import check, load_app_spec, load_contract, main


def test_implemented_routes_and_all_schemas_match_the_contract():
    assert check(load_contract(), load_app_spec(), only_implemented=True) == []
    assert main(["--only-implemented"]) == 0


def test_unrouted_paths_fail_without_the_flag():
    problems = check(load_contract(), load_app_spec())
    assert any("not routed" in p for p in problems)


def test_detects_schema_drift():
    contract, app_spec = load_contract(), load_app_spec()
    drifted = copy.deepcopy(app_spec)
    profile = drifted["components"]["schemas"]["Profile"]
    del profile["properties"]["has_resume"]
    profile["required"].remove("has_resume")
    drifted["components"]["schemas"]["Band"]["enum"].append("excellent")
    drifted["components"]["schemas"]["SkillGap"]["required"].remove("claimed")

    problems = check(contract, drifted, only_implemented=True)
    assert "schema Profile: missing property 'has_resume'" in problems
    assert any(p.startswith("schema Band: enum is") for p in problems)
    assert "schema SkillGap: 'claimed' must be required" in problems
    assert any(p.startswith("GET /v1/me -> 200: missing property 'has_resume'") for p in problems)


def test_detects_extra_route_and_wrong_operation_id():
    contract, app_spec = load_contract(), load_app_spec()
    drifted = copy.deepcopy(app_spec)
    drifted["paths"]["/v1/invented"] = {"get": {"operationId": "invented", "responses": {}}}
    drifted["paths"]["/v1/me"]["get"]["operationId"] = "whoAmI"

    problems = check(contract, drifted, only_implemented=True)
    assert "GET /v1/invented: routed, not in the contract" in problems
    assert any("operationId is whoAmI" in p for p in problems)
