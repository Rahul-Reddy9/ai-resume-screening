import json
import re
from functools import lru_cache
from pathlib import Path

from .text_preprocessor import split_sentences

SKILLS_FILE = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "skills.json"

DEFAULT_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "r", "scala", "kotlin", "php",
    "html", "css", "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring boot", "streamlit",
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "elasticsearch", "kafka",
    "docker", "kubernetes", "terraform", "jenkins", "github actions", "ci/cd", "git", "linux", "ansible",
    "aws", "azure", "gcp", "rest api", "graphql", "microservices",
    "machine learning", "deep learning", "nlp", "computer vision", "data analysis", "data science",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "spacy", "keras", "opencv",
    "tableau", "power bi", "excel", "spark", "hadoop", "airflow", "etl",
    "agile", "scrum", "jira", "unit testing", "pytest", "selenium", "devops",
    "project management", "communication", "leadership", "problem solving",
]
ALIASES = {"js": "javascript", "ts": "typescript", "k8s": "kubernetes", "postgres": "postgresql",
           "sklearn": "scikit-learn", "ml": "machine learning", "dl": "deep learning",
           "nodejs": "node.js", "node": "node.js", "powerbi": "power bi", "cicd": "ci/cd",
           "amazon web services": "aws", "google cloud": "gcp", "restful api": "rest api",
           "natural language processing": "nlp", "golang": "go"}


@lru_cache(maxsize=1)
def skill_dictionary() -> tuple[str, ...]:
    if SKILLS_FILE.exists():
        try:
            return tuple(json.loads(SKILLS_FILE.read_text()))
        except Exception:
            pass
    return tuple(DEFAULT_SKILLS)


@lru_cache(maxsize=1)
def _pattern() -> re.Pattern:
    terms = set(skill_dictionary()) | set(ALIASES)
    alt = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(rf"(?<![A-Za-z0-9+#./-])({alt})(?![A-Za-z0-9+#]|\.[A-Za-z0-9])", re.I)


def normalize_skill(s: str) -> str:
    s = s.strip().lower()
    return ALIASES.get(s, s)


def extract_skills(text: str) -> set[str]:
    return {normalize_skill(m.group(1)) for m in _pattern().finditer(text or "")}


def extract_years(text: str) -> int:
    """Largest 'N years' mention (a rough proxy; recruiters can verify in the UI)."""
    yrs = [int(m) for m in re.findall(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", text or "", re.I)]
    return max([y for y in yrs if y <= 45], default=0)


def evidence_snippets(text: str, skills: set[str], limit: int = 6) -> list[dict]:
    """Sentences from the original text that mention the given skills."""
    out = []
    for sent in split_sentences(text):
        hit = sorted(extract_skills(sent) & skills)
        if hit:
            out.append({"skills": hit, "snippet": sent[:300]})
        if len(out) >= limit:
            break
    return out
