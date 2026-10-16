import pytest

from backend.services.resume_parser import extract_text, validate_file
from backend.services.skill_extractor import evidence_snippets, extract_skills, extract_years
from tests.conftest import make_docx


def test_docx_extraction():
    data = make_docx(["Jane Doe", "5 years of experience with Python and Docker."])
    assert "Python" in extract_text(data, "cv.docx")


def test_skill_extraction_aliases_and_symbols():
    s = extract_skills("Used k8s, Postgres, C++ and Node.js; also sklearn.")
    assert {"kubernetes", "postgresql", "c++", "node.js", "scikit-learn"} <= s
    assert "java" not in extract_skills("I love javascript")


def test_years_and_evidence():
    t = "Over 7 years building APIs. Deployed services with Docker and Python."
    assert extract_years(t) == 7
    assert evidence_snippets(t, {"docker"})[0]["skills"] == ["docker"]


@pytest.mark.parametrize("name,data", [("a.exe", b"MZ.."), ("a.pdf", b"not a pdf"),
                                       ("a.docx", b"nope"), ("a.pdf", b"")])
def test_validation_rejects(name, data):
    with pytest.raises(ValueError):
        validate_file(name, data)


def test_corrupt_docx_handled():
    with pytest.raises(ValueError):
        extract_text(b"PK\x03\x04garbage", "x.docx")
