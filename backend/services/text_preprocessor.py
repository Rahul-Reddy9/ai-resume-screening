import re
import unicodedata

_sentencizer = None


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_sentences(text: str) -> list[str]:
    """spaCy rule-based sentencizer (no model download needed); falls back to regex."""
    global _sentencizer
    try:
        if _sentencizer is None:
            import spacy
            _sentencizer = spacy.blank("en")
            _sentencizer.add_pipe("sentencizer")
            _sentencizer.max_length = 3_000_000
        lines = [ln for ln in text.splitlines() if ln.strip()]
        out = []
        for ln in lines:
            out.extend(s.text.strip() for s in _sentencizer(ln).sents if s.text.strip())
        return out
    except Exception:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]
