import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_NAME_LENGTH = 80


def normalize_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("passenger_name is required")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise ValueError(f"passenger_name must be at most {MAX_NAME_LENGTH} characters")
    return cleaned


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not EMAIL_RE.fullmatch(cleaned):
        raise ValueError("passenger_email is invalid")
    return cleaned
