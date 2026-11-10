import re

# Medicine / dosing questions are out of scope: hand over to a human, never answer.
_HANDOVER = re.compile(
    r"\b(dose|dosage|dozi|tablets?|pills?|vidonge|paracetamol|ibuprofen|"
    r"antibiotics?|amoxicillin|prescribe|can i take|should i take|"
    r"dawa gani|naweza kunywa|nimeze|side effects?|madhara ya dawa)\b",
    re.IGNORECASE,
)


def needs_handover(question: str) -> bool:
    return bool(_HANDOVER.search(question))


_PII = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"(?:\+?254|0)\s?[17]\d{2}[\s-]?\d{3}[\s-]?\d{3}"), "[phone]"),
    (re.compile(r"\b\d{7,8}\b"), "[id]"),
]


def redact(text: str) -> str:
    """Strip obvious identifiers before anything is logged. Not a substitute for not logging PII."""
    for pattern, label in _PII:
        text = pattern.sub(label, text)
    return text
