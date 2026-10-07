import shutil
from pathlib import Path

import pytest
import yaml

from app import catalogue
from app.catalogue import CatalogueError, read_catalogue
from app.config import DATA_DIR

ROLE_IDS = {
    "sde-backend",
    "sde-frontend",
    "full-stack",
    "data-analyst",
    "ml-engineer",
    "devops-cloud",
    "ui-ux-designer",
}
# Skill ids used by the examples in contracts/openapi.yaml: mock and real data must line up.
CONTRACT_EXAMPLE_SKILLS = {
    "python", "fastapi", "sql", "docker", "pytest", "react", "kubernetes", "aws", "redis", "ci-cd",
    "javascript", "system-design",
}  # fmt: skip


@pytest.fixture
def broken(tmp_path):
    """Copy data/ to a temp dir, apply `edit(file_stem, mutate)`, and return the problems found."""
    shutil.copytree(DATA_DIR, tmp_path / "data")

    def run(stem: str, mutate) -> list[str]:
        path: Path = tmp_path / "data" / f"{stem}.yaml"
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        mutate(doc)
        path.write_text(yaml.safe_dump(doc), encoding="utf-8")
        with pytest.raises(CatalogueError) as exc:
            read_catalogue(tmp_path / "data")
        return exc.value.problems

    return run


def test_real_catalogue_is_valid():
    cat = catalogue.validate_catalogue()
    assert {r.id for r in cat.roles} == ROLE_IDS
    assert 55 <= len(cat.skills) <= 70
    assert cat.tutorial_names and cat.readme_templates


def test_every_role_has_8_to_14_known_skills_with_valid_importance():
    skill_ids = {s.id for s in catalogue.load_skills()}
    for role in catalogue.load_roles():
        assert 8 <= len(role.skills) <= 14, role.id
        for entry in role.skills:
            assert entry.skill_id in skill_ids
            assert entry.skill_name == catalogue.get_skill(entry.skill_id).name
            assert 1 <= entry.importance <= 3


def test_role_weights_follow_scoring_md():
    default = {
        "skill_evidence": 0.40,
        "project_quality": 0.25,
        "consistency": 0.15,
        "experience": 0.10,
        "resume_quality": 0.10,
    }
    designer = {**default, "project_quality": 0.30, "consistency": 0.05, "experience": 0.15}
    for role in catalogue.load_roles():
        expected = designer if role.id == "ui-ux-designer" else default
        assert role.weights.model_dump() == pytest.approx(expected), role.id
        assert role.is_design == (role.id == "ui-ux-designer")


def test_every_skill_has_at_least_two_resources():
    for skill in catalogue.load_skills():
        assert len(catalogue.resources_for(skill.id)) >= 2, skill.id


def test_resources_are_well_formed():
    ids = [r.id for r in catalogue.load_resources()]
    assert len(ids) == len(set(ids))
    for res in catalogue.load_resources():
        assert res.url.startswith("https://")
        assert res.hours and res.hours > 0


def test_contract_example_skills_exist():
    assert CONTRACT_EXAMPLE_SKILLS <= {s.id for s in catalogue.load_skills()}


@pytest.mark.parametrize(
    ("written", "skill_id"),
    [
        ("ReactJS", "react"),
        ("React.js", "react"),
        ("react", "react"),
        ("k8s", "kubernetes"),
        ("Postgres", "sql"),
        ("PostgreSQL", "sql"),
        ("C++", "cpp"),
        ("CI/CD", "ci-cd"),
        ("GitHub Actions", "ci-cd"),
        ("Node.js", "nodejs"),
        ("  Docker ", "docker"),
        ("Power BI", "power-bi"),
        ("HTML/CSS", "html-css"),
        ("Scikit-Learn", "scikit-learn"),
    ],
)
def test_normalize_skill(written, skill_id):
    assert catalogue.normalize_skill(written) == skill_id


def test_normalize_skill_unknown_is_none():
    assert catalogue.normalize_skill("Underwater Basket Weaving") is None
    assert catalogue.normalize_skill("") is None


def test_design_skills_have_no_code_detectors_but_code_skills_do():
    assert catalogue.get_skill("user-research").detectors.is_empty
    assert not catalogue.get_skill("docker").detectors.is_empty
    assert "Dockerfile" in catalogue.get_skill("docker").detectors.files


def test_name_lists_skip_comments():
    assert "todo" in catalogue.load_tutorial_names()
    assert not any(n.startswith("#") for n in catalogue.load_tutorial_names())
    templates = catalogue.load_readme_templates()
    assert "# React + Vite" in templates  # markers may start with '#'; comments use '//'
    assert not any(t.startswith("//") for t in templates)


# ---- the validation rules, each against a deliberately broken copy ----


def test_rejects_role_with_unknown_skill(broken):
    def mutate(doc):
        doc["roles"][0]["skills"][0]["skill"] = "cobol-on-rails"

    assert "role 'sde-backend': unknown skill 'cobol-on-rails'" in broken("roles", mutate)


def test_rejects_skill_with_fewer_than_two_resources(broken):
    def mutate(doc):
        doc["resources"] = [r for r in doc["resources"] if r["id"] != "go-tour"]

    assert "skill 'go': has 1 resource(s), needs 2" in broken("resources", mutate)


def test_rejects_alias_shared_by_two_skills(broken):
    def mutate(doc):
        next(s for s in doc["skills"] if s["id"] == "vue")["aliases"].append("React JS")

    assert "alias 'reactjs' belongs to both 'react' and 'vue'" in broken("skills", mutate)


def test_rejects_weights_that_do_not_sum_to_one(broken):
    def mutate(doc):
        doc["roles"][0]["weights"] = {**doc["roles"][0]["weights"], "consistency": 0.5}

    assert any("weights sum to" in p for p in broken("roles", mutate))


def test_rejects_unknown_detector_type_and_bad_regex(broken):
    def mutate(doc):
        docker = next(s for s in doc["skills"] if s["id"] == "docker")
        docker["detectors"]["cargo"] = ["bollard"]
        k8s = next(s for s in doc["skills"] if s["id"] == "kubernetes")
        k8s["detectors"]["content"]["regex"] = "kind:(("

    problems = broken("skills", mutate)
    assert any(p.startswith("skill 'docker': detectors.cargo") for p in problems)
    assert any("content regex does not compile" in p for p in problems)


def test_reports_all_problems_at_once(broken):
    def mutate(doc):
        doc["resources"][0]["skill_id"] = "nope"
        doc["resources"][1]["url"] = "http://insecure.example"
        doc["resources"][2]["type"] = "podcast"

    problems = broken("resources", mutate)
    assert len(problems) >= 3
