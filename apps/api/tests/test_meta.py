from app.schemas.api import Role


def test_health_needs_no_auth(client, no_dev_auth):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.2.0"
    assert "llm_provider" in body


def test_roles_come_from_the_catalogue(client):
    res = client.get("/v1/roles")
    assert res.status_code == 200
    roles = [Role.model_validate(r) for r in res.json()]
    assert "sde-backend" in {r.id for r in roles}
    for role in roles:
        assert role.skills
        assert all(1 <= s.importance <= 3 for s in role.skills)


def test_cors_allows_web_origin_and_extensions(client):
    for origin in ("http://localhost:3000", "chrome-extension://abcdefghijklmnop"):
        res = client.get("/health", headers={"Origin": origin})
        assert res.headers.get("access-control-allow-origin") == origin
    res = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in res.headers
