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
    text = (text or "")
    # Normalize newlines but preserve paragraph boundaries.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs but keep newlines.
    text = re.sub(r"[\t\f\v ]+", " ", text)
    # Collapse too many blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Trim per-line whitespace without joining lines.
    text = "\n".join(line.strip() for line in text.split("\n"))
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
        # General ag
        "agriculture",
        "farming",
        "farm",
        "crop",
        "crops",
        "cultivation",
        "field",
        "acre",
        "hectare",
        "paddy",
        "rice field",
        "ricefield",
        "nursery",
        # Water/irrigation
        "irrigation",
        "water",
        "watering",
        "drip",
        "sprinkler",
        "furrow",
        "canal",
        # Soil/nutrients
        "soil",
        "ph",
        "salinity",
        "compost",
        "manure",
        "mulch",
        "fertilizer",
        "npk",
        "nitrogen",
        "phosphorus",
        "potassium",
        "urea",
        "dap",
        "mop",
        "micronutrient",
        "zinc",
        "boron",
        # Pests/diseases
        "pest",
        "disease",
        "fungus",
        "fungal",
        "blight",
        "rust",
        "mildew",
        "wilt",
        "virus",
        "bacteria",
        "nematode",
        "insect",
        "aphid",
        "bollworm",
        "whitefly",
        "thrips",
        "pesticide",
        "insecticide",
        "herbicide",
        "fungicide",
        # Crop cycle
        "seed",
        "sowing",
        "germination",
        "transplant",
        "weeding",
        "pruning",
        "flowering",
        "fruiting",
        "harvest",
        "yield",
        # Weather
        "weather",
        "rain",
        "rainfall",
        "temperature",
        "humidity",
        "drought",
        "frost",
        "heat",
        # Livestock (still farming)
        "livestock",
        "cattle",
        "cow",
        "buffalo",
        "goat",
        "sheep",
        "poultry",
        "chicken",
        "dairy",
        # Common crops
        "rice",
        "wheat",
        "maize",
        "corn",
        "cotton",
        "sugarcane",
        "soy",
        "soybean",
        "groundnut",
        "peanut",
        "millet",
        "sorghum",
        "tomato",
        "potato",
        "onion",
    ]
    text_lower = text.lower()
    return [kw for kw in agriculture_keywords if kw in text_lower]


def farming_refusal_message() -> str:
    return (
        "I can only help with farming and agriculture topics (crops, soil, irrigation, pests/diseases, "
        "fertilizers, livestock, and related practices). Please ask a farming-related question."
    )


def is_farming_related(text: str, session_memory: dict[str, Any] | None = None) -> bool:
    """Strict allow-gate: only allow clearly agriculture/farming related messages.

    Uses keyword presence and a small follow-up allowance if the session already has farming context.
    """

    text = (text or "").strip()
    if not text:
        return False

    keywords = extract_keywords(text)
    if keywords:
        return True

    # If the user already discussed a crop/location in this session, allow short follow-ups
    # that are typical in farming conversations (but still keep it strict).
    if session_memory and (session_memory.get("crop") or session_memory.get("location")):
        followup_cues = [
            "how often",
            "how much",
            "when",
            "what should i do",
            "dose",
            "spray",
            "watering",
            "water",
            "irrigate",
            "fertilize",
            "fertiliser",
            "symptom",
            "treatment",
        ]
        lower = text.lower()
        if len(lower) <= 120 and any(cue in lower for cue in followup_cues):
            return True

    return False
