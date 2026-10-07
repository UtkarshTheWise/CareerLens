from pathlib import Path

import pytest

from app.errors import ApiError
from app.services.ingest import MAX_UPLOAD_BYTES, extract_text, restore_pii, strip_pii

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_pdf_text_and_page_count():
    doc = extract_text("resume.pdf", _read("resume.pdf"))
    assert doc.page_count == 2
    assert "Aarav Mehta" in doc.text
    assert "Reduced API response time by 35%" in doc.text
    assert "campus-api" in doc.text  # second page


def test_docx_text_includes_tables():
    doc = extract_text("resume.docx", _read("resume.docx"))
    assert doc.page_count is None
    assert "Python, FastAPI, SQL" in doc.text
    assert "English, Hindi" in doc.text


def test_type_is_detected_from_content_not_extension():
    assert extract_text("resume.txt", _read("resume.pdf")).page_count == 2
    with pytest.raises(ApiError) as exc:
        extract_text("resume.pdf", b"just some plain text pretending to be a pdf")
    assert (exc.value.status_code, exc.value.code) == (422, "unsupported_file")


def test_rejects_files_over_5_mb():
    with pytest.raises(ApiError) as exc:
        extract_text("big.pdf", b"%PDF-" + b"0" * MAX_UPLOAD_BYTES)
    assert (exc.value.status_code, exc.value.code) == (413, "payload_too_large")


def test_pdf_without_text_layer_is_reported_kindly():
    with pytest.raises(ApiError) as exc:
        extract_text("scan.pdf", _read("no_text.pdf"))
    assert (exc.value.status_code, exc.value.code) == (422, "no_text_extracted")
    assert "text-based" in exc.value.message


def test_damaged_file_is_a_422_not_a_crash():
    with pytest.raises(ApiError) as exc:
        extract_text("broken.pdf", b"%PDF-1.4\nthis is not really a pdf")
    assert exc.value.status_code == 422


# ---------------------------------------------------------------- PII

RESUME = extract_text("resume.pdf", _read("resume.pdf")).text if (FIXTURES / "resume.pdf").exists() else ""


def test_strips_email_phone_urls_and_name():
    stripped = strip_pii(RESUME)
    for secret in (
        "aarav.mehta@example.com",
        "98765 43210",
        "careerlens-demo",
        "aarav-mehta-demo",
        "Aarav",
        "Mehta",
    ):
        assert secret.lower() not in stripped.text.lower(), secret
    assert stripped.text.splitlines()[0] == "[NAME]"
    assert "[EMAIL_1]" in stripped.text and "[PHONE_1]" in stripped.text and "[URL_1]" in stripped.text


def test_keeps_years_percentages_and_metrics():
    stripped = strip_pii(RESUME).text
    for kept in (
        "2023 - 2027",
        "2025-05 to 2025-07",
        "35%",
        "10,000 requests",
        "40 pytest tests",
        "CGPA 8.4",
    ):
        assert kept in stripped, kept
    assert "Python, FastAPI, SQL, Docker" in stripped


@pytest.mark.parametrize(
    "phone",
    ["+91 98765 43210", "+91-9876543210", "9876543210", "(044) 2345 6789", "+1 415-555-0132", "098765 43210"],
)
def test_phone_formats(phone):
    stripped = strip_pii(f"Skills\nCall me on {phone} today")
    assert phone not in stripped.text
    assert stripped.mapping["[PHONE_1]"] == phone


@pytest.mark.parametrize(
    "text",
    [
        "Built in 2021-2023 and 2023-2024",
        "Scored 9.1 CGPA, rank 1200 of 45000",
        "ASP.NET and Node.js",
        "v1.2.3",
    ],
)
def test_non_pii_is_untouched(text):
    assert strip_pii("Skills\n" + text).text == "Skills\n" + text


def test_known_name_is_removed_even_without_a_header_line():
    stripped = strip_pii(
        "SUMMARY\nPriya Raman is a backend developer. Priya built APIs.", known_names=["Priya Raman"]
    )
    assert "Priya" not in stripped.text and "Raman" not in stripped.text
    assert stripped.text.count("[NAME]") == 2


def test_heading_is_not_mistaken_for_a_name():
    assert strip_pii("Curriculum Vitae\nPython developer").text.startswith("Curriculum Vitae")


def test_same_value_gets_the_same_placeholder():
    stripped = strip_pii("Skills\nmail a@b.co or A@B.co, not c@d.co")
    assert stripped.text == "Skills\nmail [EMAIL_1] or [EMAIL_1], not [EMAIL_2]"


def test_restore_round_trips_through_nested_structures():
    stripped = strip_pii(RESUME)
    assert (
        restore_pii(stripped.text, stripped.mapping).count("https://github.com/careerlens-demo/campus-api")
        == 1
    )
    nested = {"links": ["[URL_1]"], "inner": [{"note": "mail [EMAIL_1]"}], "n": 3}
    restored = restore_pii(nested, stripped.mapping)
    assert restored["links"] == [stripped.mapping["[URL_1]"]]
    assert restored["inner"][0]["note"] == "mail aarav.mehta@example.com"
    assert restored["n"] == 3
