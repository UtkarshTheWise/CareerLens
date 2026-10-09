from pathlib import Path

import pytest

from app.errors import ApiError
from app.services.ingest import MAX_TEXT_CHARS, MAX_UPLOAD_BYTES, extract_text, restore_pii, strip_pii

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


BUILT_RESUME = (
    "Asha Verma\nasha@example.com | +91 98765 43210\nhttps://github.com/ashav\n\n"
    "SKILLS\nPython, SQL, FastAPI\n\nPROJECTS\nCampus API\nA REST API for hostel requests.\n"
    "https://github.com/ashav/campus-api\n"
)


def test_plain_text_resume_is_read_with_unknown_page_count():
    doc = extract_text("resume.txt", BUILT_RESUME.encode())
    assert doc.page_count is None
    assert doc.text.startswith("Asha Verma\n")
    assert "Python, SQL, FastAPI" in doc.text


@pytest.mark.parametrize("name", ["resume", "resume.doc", "resume.pdf", None])
def test_plain_text_needs_a_txt_name(name):
    with pytest.raises(ApiError) as exc:
        extract_text(name, BUILT_RESUME.encode())
    assert (exc.value.status_code, exc.value.code) == (422, "unsupported_file")


@pytest.mark.parametrize("data", [b"\xff\xfe\x00\x01 not utf8 " * 10, ("a" * 40 + "\x01").encode()])
def test_non_utf8_or_control_characters_in_txt_are_refused(data):
    with pytest.raises(ApiError) as exc:
        extract_text("resume.txt", data)
    assert (exc.value.status_code, exc.value.code) == (422, "unsupported_file")


def test_short_plain_text_has_no_text_extracted():
    with pytest.raises(ApiError) as exc:
        extract_text("resume.txt", b"hello")
    assert (exc.value.status_code, exc.value.code) == (422, "no_text_extracted")


def test_bom_and_crlf_are_normalised():
    doc = extract_text("resume.txt", b"\xef\xbb\xbf" + BUILT_RESUME.replace("\n", "\r\n").encode())
    assert "\r" not in doc.text and doc.text.startswith("Asha Verma\n")


def test_too_long_plain_text_is_refused():
    with pytest.raises(ApiError) as exc:
        extract_text("resume.txt", ("word " * (MAX_TEXT_CHARS // 4)).encode())
    assert (exc.value.status_code, exc.value.code) == (422, "unsupported_file")


def test_builder_layout_loses_name_contact_and_links_before_the_llm():
    stripped = strip_pii(extract_text("resume.txt", BUILT_RESUME.encode()).text, known_names=["Asha Verma"])
    for private in ("Asha", "asha@example.com", "98765", "github.com/ashav"):
        assert private not in stripped.text
    assert "Python, SQL, FastAPI" in stripped.text


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


def test_header_name_detection_can_be_switched_off_for_titles():
    text = "Campus API\nA REST API for events"
    assert strip_pii(text, ["Priya Raman"]).text.startswith("[NAME]")  # a resume: the first line is the name
    kept = strip_pii(text, ["Priya Raman"], header_name=False).text
    assert kept == text  # a README or description: the first line is a title


def test_a_pdf_with_too_many_pages_is_refused_before_it_is_read(monkeypatch):
    from pathlib import Path

    from app.services import ingest

    monkeypatch.setattr(ingest, "MAX_PDF_PAGES", 1)  # the two-page fixture résumé is now "too long"
    data = (Path(__file__).parent / "fixtures" / "resume.pdf").read_bytes()
    with pytest.raises(ApiError) as caught:
        extract_text("long.pdf", data)
    assert caught.value.status_code == 422 and "pages" in caught.value.message


def test_a_docx_that_unpacks_to_a_huge_size_is_refused():
    import io
    import zipfile

    from app.services import ingest

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"0" * (ingest.MAX_DOCX_UNPACKED_BYTES + 1))
    with pytest.raises(ApiError) as caught:
        extract_text("bomb.docx", buffer.getvalue())
    assert caught.value.status_code == 422
