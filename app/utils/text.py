import re
import uuid
from datetime import datetime
from typing import Any


def generate_id() -> str:
    return str(uuid.uuid4())


def generate_doc_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def generate_chunk_id() -> str:
    return f"chunk_{uuid.uuid4().hex[:12]}"


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_agriculture_terms(text: str) -> str:
    replacements = {
        r"\bcrop?s\b": "crop",
        r"\bfarm(?:ing|er)?s?\b": "farming",
        r"\bpesticides?\b": "pesticide",
        r"\bfertilizer(?:s)?\b": "fertilizer",
        r"\birrigation\b": "irrigation",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def remove_duplicate_lines(text: str) -> str:
    lines = text.split("\n")
    seen = set()
    result = []
    for line in lines:
        normalized = line.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(line)
    return "\n".join(result)


def extract_keywords(text: str) -> list[str]:
    agriculture_keywords = [
        "crop", "disease", "fertilizer", "soil", "irrigation", "pest",
        "yield", "harvest", "seed", "plant", "growth", "weather",
        "rainfall", "temperature", "humidity", "nitrogen", "phosphorus",
        "potassium", "organic", "pesticide", "herbicide", "insecticide",
    ]
    text_lower = text.lower()
    return [kw for kw in agriculture_keywords if kw in text_lower]