import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RENDER = ROOT / "render.yaml"
KEEPALIVE = ROOT / ".github" / "workflows" / "keepalive.yml"
SECRET_SHAPES = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}|AIza[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_|postgres(?:ql)?(?:\+\w+)?://\S+:\S+@"
)


def render_service() -> dict:
    [service] = yaml.safe_load(RENDER.read_text(encoding="utf-8"))["services"]
    return service


def test_render_describes_one_free_web_service_for_apps_api():
    service = render_service()
    assert service["type"] == "web" and service["plan"] == "free" and service["rootDir"] == "apps/api"
    assert service["healthCheckPath"] == "/health"
    assert "uvicorn app.main:app" in service["startCommand"] and "$PORT" in service["startCommand"]
    assert "--frozen" in service["buildCommand"]


def test_render_turns_on_the_production_guard_and_never_dev_auth():
    env = {e["key"]: e for e in render_service()["envVars"]}
    assert env["ENVIRONMENT"]["value"] == "production" and env["DEV_AUTH"]["value"] == "0"


def test_every_secret_is_left_for_the_dashboard():
    env = {e["key"]: e for e in render_service()["envVars"]}
    for key in ("DATABASE_URL", "SUPABASE_JWT_SECRET", "GEMINI_API_KEY", "GROQ_API_KEY", "GITHUB_TOKEN"):
        assert env[key].get("sync") is False and "value" not in env[key], key
    for e in env.values():
        assert "value" in e or e.get("sync") is False  # nothing half-defined


def test_no_secret_shaped_text_in_the_deploy_files():
    for path in (RENDER, KEEPALIVE, ROOT / "apps" / "api" / ".env.example"):
        assert not SECRET_SHAPES.search(path.read_text(encoding="utf-8")), path.name


def test_every_setting_render_names_exists_in_the_app():
    from app.config import Settings

    fields = {name.upper() for name in Settings.model_fields}
    for e in render_service()["envVars"]:
        if e["key"] != "PYTHON_VERSION":
            assert e["key"] in fields, e["key"]


def test_keepalive_runs_daily_and_by_hand_and_pings_health_with_retries():
    doc = yaml.safe_load(KEEPALIVE.read_text(encoding="utf-8"))
    triggers = doc.get("on") or doc[True]  # YAML reads a bare `on` as the boolean True
    assert triggers["schedule"][0]["cron"].split()[2:] == ["*", "*", "*"]  # every day
    assert "workflow_dispatch" in triggers
    assert doc["permissions"] == {}
    step = doc["jobs"]["ping"]["steps"][0]
    assert step["env"]["API_URL"] == "${{ secrets.API_URL }}"
    assert "/health" in step["run"] and "--retry" in step["run"] and "--fail" in step["run"]
    assert doc["jobs"]["ping"]["timeout-minutes"] <= 10


def test_the_example_env_lists_every_setting_the_readme_documents():
    example = (ROOT / "apps" / "api" / ".env.example").read_text(encoding="utf-8")
    readme = (ROOT / "apps" / "api" / "README.md").read_text(encoding="utf-8")
    for key in (
        "SUPABASE_URL",
        "SUPABASE_JWT_SECRET",
        "PLACEMENT_STAFF",
        "ENVIRONMENT",
        "DEV_AUTH",
        "CORS_ORIGINS",
    ):
        assert key in example and key in readme, key
