from backend.services import ranking_engine as re_
from backend.services.matching_engine import similarity, skill_coverage

JD = "Looking for a backend engineer with Python, FastAPI, PostgreSQL and Docker experience."


def test_skill_coverage():
    k, matched, missing = skill_coverage(["Python", "Docker", "Go"], {"python", "docker"})
    assert round(k, 1) == 66.7 and missing == ["go"]


def test_similarity_orders_relevant_higher():
    good = "Backend engineer: Python, FastAPI, PostgreSQL, Docker."
    bad = "Pastry chef with experience in baking bread and cakes."
    assert similarity(JD, good) > similarity(JD, bad)


def test_ranking_and_weights():
    good = re_.screen_resume("5 years backend work. Built Python FastAPI services on PostgreSQL with Docker.", JD, [], 3)
    bad = re_.screen_resume("Pastry chef with 10 years baking bread.", JD, [], 3)
    assert good["final_score"] > bad["final_score"]
    assert re_.final_score(100, 100, 100) == 100


def test_manual_correction_raises_score():
    r = re_.screen_resume("Python developer.", JD, ["python", "docker"], 0)
    fixed = re_.apply_corrections(r, ["Docker"])
    assert fixed["final_score"] > r["final_score"] and fixed["missing_skills"] == []
