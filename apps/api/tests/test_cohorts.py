import csv
import io
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid4, uuid5

from app.db import models
from app.db.base import SessionLocal
from app.schemas.api import (
    AnalysisReport,
    Band,
    EvidenceLevel,
    ProjectAudit,
    SkillClaim,
    SkillGap,
    Understanding,
)
from app.services import cohorts, scoring
from tests.conftest import assert_error_shape
from tests.scoring_helpers import code_project, rich_inputs
from tests.scoring_helpers import inputs as bare_inputs

CID = str(uuid4())


def uid(name: str) -> str:
    return str(uuid5(NAMESPACE_DNS, name))


def band_for(score: float) -> Band:
    return Band.not_ready if score < 50 else Band.developing if score < 75 else Band.ready


def claim(skill: str, level: str, claimed: bool = True) -> SkillClaim:
    return SkillClaim(
        skill_id=skill, skill_name=skill.title(), claimed=claimed, level=EvidenceLevel(level), reason="r",
        evidence_ids=[],
    )  # fmt: skip


def project(
    title: str, understanding: str, skills=(), score: float = 70, counted: bool = True
) -> ProjectAudit:
    return ProjectAudit(
        project_id=f"proj-{title}", title=title, kind="code", score=score, counted_in_score=counted,
        detected_skills=list(skills), flags=[], self_reported=False, understanding=Understanding(understanding),
    )  # fmt: skip


def row(name: str, score: float, coverage: float = 100, department=None, claims=(), gaps=(), projects=()):
    profile = models.Profile(id=uid(name), name=name, department=department)
    return cohorts.Row(
        profile,
        uid("analysis-" + name),
        score,
        band_for(score),
        coverage,
        list(claims),
        list(gaps),
        list(projects),
    )


# ---------------------------------------------------------------- the maths (hand-checked)


def sample_rows() -> list[cohorts.Row]:
    return [
        row("A", 9.9, claims=[claim("docker", "weak"), claim("terraform", "missing", False)]),
        row(
            "B",
            10,
            department="CSE",
            claims=[claim("docker", "unverified"), claim("terraform", "missing", False)],
        ),
        row(
            "C",
            49.9,
            department="IT",
            claims=[
                claim("docker", "strong"),
                claim("terraform", "missing", False),
                claim("redis", "missing", False),
            ],
            projects=[project("c", "demonstrated", ["docker"])],
        ),  # fmt: skip
        row("D", 50, 40, "IT", projects=[project("d", "partial")]),
        row("E", 50, 39.9, "IT", projects=[project("e", "not_demonstrated")]),
        row("F", 89.9),
        row("G", 100, department="CSE"),
    ]


def test_histogram_bands_median_and_at_risk_use_the_documented_edges():
    insights = cohorts.aggregate(sample_rows(), [r.profile for r in sample_rows()], CID, "sde-backend")
    counts = {b.bucket: b.count for b in insights.histogram}
    assert list(counts) == [
        "0-9",
        "10-19",
        "20-29",
        "30-39",
        "40-49",
        "50-59",
        "60-69",
        "70-79",
        "80-89",
        "90-100",
    ]
    assert counts == {
        "0-9": 1, "10-19": 1, "20-29": 0, "30-39": 0, "40-49": 1, "50-59": 2, "60-69": 0, "70-79": 0,
        "80-89": 1, "90-100": 1,
    }  # fmt: skip
    assert (insights.bands.not_ready, insights.bands.developing, insights.bands.ready) == (3, 2, 2)
    assert insights.median_score == 50.0
    # score < 50 (A, B, C) or coverage < 40 (E): D sits exactly on both limits and is not at risk
    assert insights.at_risk_count == 4
    assert (insights.student_count, insights.analysed_count) == (7, 7)


def test_median_of_an_even_count_and_of_nothing():
    pair = [row("A", 10), row("B", 20)]
    assert cohorts.aggregate(pair, [r.profile for r in pair], CID, "sde-backend").median_score == 15.0
    empty = cohorts.aggregate([], [], CID, "sde-backend")
    assert empty.median_score is None and empty.median_coverage is None and empty.at_risk_count == 0
    assert sum(b.count for b in empty.histogram) == 0 and empty.understanding.quizzed == 0


def test_top_missing_skills_count_students_and_break_ties_by_name():
    insights = cohorts.aggregate(sample_rows(), [r.profile for r in sample_rows()], CID, "sde-backend")
    assert [(m.skill_id, m.students) for m in insights.top_missing_skills] == [("terraform", 3), ("redis", 1)]


def test_unverified_rate_needs_two_claimants_and_counts_weak_and_unverified():
    insights = cohorts.aggregate(sample_rows(), [r.profile for r in sample_rows()], CID, "sde-backend")
    rates = insights.unverified_rate_by_skill
    assert [(r.skill_id, r.claimed_by, r.unverified_rate) for r in rates] == [("docker", 3, 66.7)]
    solo = [row("A", 50, claims=[claim("kubernetes", "unverified")])]
    assert cohorts.aggregate(solo, [solo[0].profile], CID, "sde-backend").unverified_rate_by_skill == []


def test_understanding_summary_uses_the_top_counted_project():
    rows = sample_rows()
    low = project("low", "not_demonstrated", score=10)
    top = project("top", "demonstrated", score=90)
    rows.append(row("H", 60, projects=[low, top, project("hidden", "partial", score=99, counted=False)]))
    understanding = cohorts.aggregate(rows, [r.profile for r in rows], CID, "sde-backend").understanding
    assert (understanding.quizzed, understanding.demonstrated) == (4, 2)
    assert (understanding.partial, understanding.not_demonstrated) == (1, 1)


def test_built_and_explained_needs_a_backed_claim_and_a_demonstrated_project():
    rows = sample_rows()
    understanding = cohorts.aggregate(rows, [r.profile for r in rows], CID, "sde-backend").understanding
    # docker: 3 claimants; only C has a strong claim AND a demonstrated project that shows docker
    assert [(s.skill_id, s.claimed_by, s.built_and_explained_rate) for s in understanding.by_skill] == [
        ("docker", 3, 33.3)
    ]


def test_no_quiz_results_means_no_per_skill_understanding():
    rows = [
        row("A", 50, claims=[claim("docker", "strong")]),
        row("B", 60, claims=[claim("docker", "strong")]),
    ]
    understanding = cohorts.aggregate(rows, [r.profile for r in rows], CID, "sde-backend").understanding
    assert understanding.quizzed == 0 and understanding.by_skill == []


def test_by_department_counts_every_student_but_medians_only_analysed_ones():
    rows = sample_rows()
    profiles = [r.profile for r in rows] + [models.Profile(id=uid("X"), name="X", department="CSE")]
    by_dept = {d.department: d for d in cohorts.aggregate(rows, profiles, CID, "sde-backend").by_department}
    assert (by_dept["CSE"].students, by_dept["CSE"].median_score) == (3, 55.0)  # B=10, G=100; X not analysed
    assert (by_dept["IT"].students, by_dept["IT"].median_score) == (3, 50.0)  # C=49.9, D=50, E=50
    assert list(by_dept) == ["CSE", "IT"]


def test_students_are_weakest_first_and_filterable():
    rows = sample_rows()
    rows[0].gaps = [SkillGap(gap_id="g", skill_id="x", skill_name="CI/CD", importance=3, claimed=False,
                             level=EvidenceLevel.missing, estimated_gain=4)]  # fmt: skip
    everyone = cohorts.students(rows)
    assert [s.name for s in everyone] == ["A", "B", "C", "D", "E", "F", "G"]
    assert everyone[0].top_gap == "CI/CD" and everyone[1].top_gap is None
    assert everyone[2].understanding == Understanding.demonstrated
    assert everyone[5].understanding == Understanding.not_taken
    assert [s.name for s in cohorts.students(rows, cohorts.StudentQuery(at_risk_only=True))] == [
        "A", "B", "C", "E",
    ]  # fmt: skip


# ---------------------------------------------------------------- finding students (filters)


def finder_rows() -> list[cohorts.Row]:
    return [
        row("Asha", 82, claims=[claim("python", "strong"), claim("docker", "strong")]),
        row("Bela", 71, claims=[claim("python", "strong"), claim("docker", "moderate")]),
        row("Chen", 90, claims=[claim("python", "moderate"), claim("docker", "weak")]),
        row("Dev", 40, claims=[claim("python", "strong"), claim("docker", "unverified")]),
        row("Esha", 66, claims=[claim("docker", "strong")]),
        row("Farid", 55),  # no claims at all
    ]


def names(found) -> list[str]:
    return [s.name for s in found]


def test_skill_filter_needs_verified_evidence_by_default():
    found = cohorts.students(finder_rows(), cohorts.StudentQuery(skills=("docker",)))
    assert names(found) == ["Esha", "Bela", "Asha"]  # strong or moderate; weakest score first
    assert {s.name: [m.level for m in s.matched_skills] for s in found}["Bela"] == [EvidenceLevel.moderate]


def test_min_level_widens_or_narrows_the_match():
    strong = cohorts.StudentQuery(skills=("docker",), min_level=EvidenceLevel.strong)
    assert names(cohorts.students(finder_rows(), strong)) == ["Esha", "Asha"]
    weak = cohorts.StudentQuery(skills=("docker",), min_level=EvidenceLevel.weak)
    assert names(cohorts.students(finder_rows(), weak)) == ["Esha", "Bela", "Asha", "Chen"]
    unverified = cohorts.StudentQuery(skills=("docker",), min_level=EvidenceLevel.unverified)
    assert names(cohorts.students(finder_rows(), unverified)) == ["Dev", "Esha", "Bela", "Asha", "Chen"]


def test_skill_match_all_vs_any():
    both = cohorts.StudentQuery(skills=("python", "docker"))
    assert names(cohorts.students(finder_rows(), both)) == ["Bela", "Asha"]  # Chen's docker is only weak
    either = cohorts.StudentQuery(skills=("python", "docker"), skill_match="any")
    assert names(cohorts.students(finder_rows(), either)) == ["Dev", "Esha", "Bela", "Asha", "Chen"]
    only = cohorts.students(finder_rows(), cohorts.StudentQuery(skills=("python", "docker")))
    assert [m.skill_id for m in only[0].matched_skills] == ["python", "docker"]  # request order


def test_a_skill_nobody_has_matches_nobody():
    assert cohorts.students(finder_rows(), cohorts.StudentQuery(skills=("terraform",))) == []


def test_min_score_band_sort_and_limit():
    rows = finder_rows()
    assert names(cohorts.students(rows, cohorts.StudentQuery(min_score=66))) == ["Esha", "Bela", "Asha", "Chen"]
    ready = cohorts.StudentQuery(bands=frozenset({Band.ready}))
    assert names(cohorts.students(rows, ready)) == ["Asha", "Chen"]
    assert names(cohorts.students(rows, cohorts.StudentQuery(sort="score_desc"))) == [
        "Chen", "Asha", "Bela", "Esha", "Farid", "Dev",
    ]  # fmt: skip
    assert names(cohorts.students(rows, cohorts.StudentQuery(sort="name"))) == [
        "Asha", "Bela", "Chen", "Dev", "Esha", "Farid",
    ]  # fmt: skip
    assert names(cohorts.students(rows, cohorts.StudentQuery(sort="coverage_desc", limit=2))) == ["Chen", "Asha"]


def test_company_asks_for_two_good_students_with_a_skill():
    query = cohorts.StudentQuery(skills=("docker",), min_score=65, sort="score_desc", limit=2)
    found = cohorts.students(finder_rows(), query)
    assert names(found) == ["Asha", "Bela"]
    assert all(s.score >= 65 and s.matched_skills for s in found)


def test_matched_skills_is_empty_without_a_skill_filter():
    assert all(s.matched_skills == [] for s in cohorts.students(finder_rows()))


def test_csv_has_a_header_one_row_per_student_and_neutralises_formulas():
    rows = [row("=HYPERLINK(1)", 40), row("Plain", 80)]
    rows[0].profile.github_username = "@someone"
    parsed = list(csv.reader(io.StringIO(cohorts.to_csv(cohorts.students(rows)))))
    assert parsed[0] == cohorts.CSV_COLUMNS and len(parsed) == 3
    first = dict(zip(parsed[0], parsed[1], strict=True))
    assert first["name"] == "'=HYPERLINK(1)" and first["github_username"] == "'@someone"
    assert first["band"] == "not_ready" and first["at_risk"] == "True"
    assert "email" not in cohorts.CSV_COLUMNS


# ---------------------------------------------------------------- routes


def _store(db, inputs, role="sde-backend", cohort=None, name="Student", department="CSE"):
    result = scoring.score(inputs, role)
    profile = models.Profile(name=name, department=department, cohort_id=cohort, github_username=None)
    db.add(profile)
    db.flush()
    report = AnalysisReport(
        score=result.breakdown, coverage=result.coverage, claims=result.claims, gaps=result.gaps,
        projects=result.projects, role_fits=[], roadmap=[], evidence=result.evidence, notes=[],
    )  # fmt: skip
    analysis = models.Analysis(
        profile_id=profile.id, role_id=role, status="done", progress=100, score=result.breakdown.total,
        coverage=result.coverage, report=report.model_dump(mode="json"), signals=inputs.model_dump(mode="json"),
    )  # fmt: skip
    db.add(analysis)
    return profile, analysis


def _cohort() -> str:
    with SessionLocal() as db:
        cohort = models.Cohort(name="B.Tech CSE 2027", department="CSE", year=2027)
        db.add(cohort)
        db.flush()
        strong = rich_inputs()
        thin = bare_inputs(projects=[code_project("shop-api", skills=["python"])], github_linked=True)
        _store(db, strong, cohort=cohort.id, name="Strong Student")
        _store(db, thin, cohort=cohort.id, name="Thin Student", department="IT")
        db.add(models.Profile(name="Not Analysed", cohort_id=cohort.id))  # no analysis yet
        db.commit()
        return cohort.id


def test_list_cohorts_counts_students(client):
    cid = _cohort()
    with SessionLocal() as db:
        db.add(models.Cohort(name="Empty"))
        db.commit()
    res = client.get("/v1/cohorts")
    assert res.status_code == 200
    by_name = {c["name"]: c for c in res.json()}
    assert by_name["B.Tech CSE 2027"] == {
        "id": cid, "name": "B.Tech CSE 2027", "department": "CSE", "year": 2027, "student_count": 3,
    }  # fmt: skip
    assert by_name["Empty"]["student_count"] == 0


def test_insights_route_matches_the_contract_shape(client):
    cid = _cohort()
    res = client.get(f"/v1/cohorts/{cid}/insights", params={"role_id": "sde-backend"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["student_count"], body["analysed_count"]) == (3, 2)
    assert sum(b["count"] for b in body["histogram"]) == 2 and len(body["histogram"]) == 10
    assert sum(body["bands"].values()) == 2
    assert body["understanding"] == {"quizzed": 0, "demonstrated": 0, "partial": 0, "not_demonstrated": 0,
                                     "by_skill": []}  # fmt: skip
    assert {d["department"] for d in body["by_department"]} == {"CSE", "IT"}


def test_other_role_views_rescore_the_stored_signals(client):
    cid = _cohort()
    students = client.get(f"/v1/cohorts/{cid}/students", params={"role_id": "data-analyst"}).json()
    expected = scoring.score(rich_inputs(), "data-analyst").breakdown.total
    assert next(s for s in students if s["name"] == "Strong Student")["score"] == expected
    own = client.get(f"/v1/cohorts/{cid}/students", params={"role_id": "sde-backend"}).json()
    assert next(s for s in own if s["name"] == "Strong Student")["score"] == (
        scoring.score(rich_inputs(), "sde-backend").breakdown.total
    )


def test_students_route_sorts_weakest_first_and_filters_at_risk(client):
    cid = _cohort()
    students = client.get(f"/v1/cohorts/{cid}/students", params={"role_id": "sde-backend"}).json()
    assert [s["name"] for s in students] == ["Thin Student", "Strong Student"]  # unanalysed student is absent
    assert students[0]["analysis_id"] and students[0]["understanding"] == "not_taken"
    risky = client.get(
        f"/v1/cohorts/{cid}/students", params={"role_id": "sde-backend", "at_risk_only": "true"}
    ).json()
    assert [s["name"] for s in risky] == [s["name"] for s in students if s["at_risk"]]


def test_students_route_filters_by_repeated_skills_score_and_limit(client):
    cid = _cohort()
    path = f"/v1/cohorts/{cid}/students"
    both = client.get(path, params=[("role_id", "sde-backend"), ("skill", "python"), ("skill", "docker")]).json()
    assert [s["name"] for s in both] == ["Strong Student"]
    assert [(m["skill_id"], m["level"]) for m in both[0]["matched_skills"]] == [
        ("python", "strong"), ("docker", "strong"),
    ]  # fmt: skip
    top = client.get(
        path, params={"role_id": "sde-backend", "sort": "score_desc", "limit": 1, "min_score": 0}
    ).json()
    assert [s["name"] for s in top] == ["Strong Student"]
    nobody = client.get(path, params={"role_id": "sde-backend", "skill": "kubernetes"}).json()
    assert nobody == []  # kubernetes is only an unverified claim
    weak_ok = client.get(
        path, params={"role_id": "sde-backend", "skill": "kubernetes", "min_level": "unverified"}
    ).json()
    assert [s["name"] for s in weak_ok] == ["Strong Student"]
    bands = client.get(path, params=[("role_id", "sde-backend"), ("band", "not_ready")]).json()
    assert all(s["band"] == "not_ready" for s in bands)


def test_students_route_rejects_bad_filters(client):
    cid = _cohort()
    path = f"/v1/cohorts/{cid}/students"
    many = [("role_id", "sde-backend")] + [("skill", "python")] * 11
    bad = [
        {"role_id": "sde-backend", "skill": "not-a-skill"},
        {"role_id": "sde-backend", "min_score": 101},
        {"role_id": "sde-backend", "limit": 0},
        {"role_id": "sde-backend", "band": "excellent"},
        {"role_id": "sde-backend", "sort": "random"},
        {"role_id": "sde-backend", "min_level": "missing"},
        many,
    ]
    for params in bad:
        res = client.get(path, params=params)
        assert res.status_code == 422, params
        assert_error_shape(res.json())


def test_export_route_applies_the_same_filters(client):
    cid = _cohort()
    res = client.get(
        f"/v1/cohorts/{cid}/export", params={"role_id": "sde-backend", "skill": "docker", "limit": 5}
    )
    rows = list(csv.DictReader(io.StringIO(res.text)))
    assert [r["name"] for r in rows] == ["Strong Student"]
    assert rows[0]["matched_skills"] == "Docker (strong)"


def test_filter_params_are_in_the_contract_and_the_app():
    import yaml

    from app.main import app

    contract = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text("utf-8"))
    for path, op in (("/v1/cohorts/{cohort_id}/students", "get"), ("/v1/cohorts/{cohort_id}/export", "get")):
        in_contract = set()
        for param in contract["paths"][path].get("parameters", []):
            param = contract["components"]["parameters"][param["$ref"].split("/")[-1]] if "$ref" in param else param
            if param["in"] == "query":
                in_contract.add(param["name"])
        in_app = {p["name"] for p in app.openapi()["paths"][path][op].get("parameters", []) if p["in"] == "query"}
        assert in_contract == in_app, path


def test_export_route_returns_a_csv_attachment(client):
    cid = _cohort()
    res = client.get(f"/v1/cohorts/{cid}/export", params={"role_id": "sde-backend"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert res.headers["content-disposition"] == 'attachment; filename="b-tech-cse-2027-sde-backend.csv"'
    rows = list(csv.DictReader(io.StringIO(res.text)))
    assert [r["name"] for r in rows] == ["Thin Student", "Strong Student"]


def test_cohort_routes_validate_cohort_and_role(client):
    cid = _cohort()
    for path in ("insights", "students", "export"):
        unknown_role = client.get(f"/v1/cohorts/{cid}/{path}", params={"role_id": "astronaut"})
        assert unknown_role.status_code == 422
        assert_error_shape(unknown_role.json())
        no_cohort = client.get(f"/v1/cohorts/{uuid4()}/{path}", params={"role_id": "sde-backend"})
        assert no_cohort.status_code == 404
        assert_error_shape(no_cohort.json())
        assert client.get(f"/v1/cohorts/{cid}/{path}").status_code == 422  # role_id is required
