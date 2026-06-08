import re
import mlflow
import time
from pydantic import BaseModel


class PatternMatch(BaseModel):
    page_number: int
    pattern_type: str
    match: str
    context: str


PROBLEMATIC_GERUNDS = [
    "logrando", "permitiendo", "generando", "obteniendo",
    "mejorando", "reduciendo", "aumentando", "demostrando", "mostrando"
]

ANAPHORA_PATTERNS = [
    "el cual", "la cual", "los cuales", "las cuales",
    "el mismo", "la misma", "los mismos", "las mismas"
]


def detect_gerunds(text: str, page_number: int) -> list[PatternMatch]:
    matches = []
    for gerund in PROBLEMATIC_GERUNDS:
        for m in re.finditer(rf'\b{gerund}\b', text, re.IGNORECASE):
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            matches.append(PatternMatch(
                page_number=page_number,
                pattern_type="gerundio",
                match=m.group(),
                context=text[start:end].strip()
            ))
    return matches


def detect_anaphora(text: str, page_number: int) -> list[PatternMatch]:
    matches = []
    for anaphora in ANAPHORA_PATTERNS:
        for m in re.finditer(rf'\b{anaphora}\b', text, re.IGNORECASE):
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            matches.append(PatternMatch(
                page_number=page_number,
                pattern_type="anáfora",
                match=m.group(),
                context=text[start:end].strip()
            ))
    return matches


@mlflow.trace(name="pattern_detector")
def detect_patterns(text: str, page_number: int) -> list[PatternMatch]:
    start_time = time.time()

    matches = []
    matches.extend(detect_gerunds(text, page_number))
    matches.extend(detect_anaphora(text, page_number))

    latency = time.time() - start_time

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "page_number": page_number,
            "gerunds_found": len([m for m in matches if m.pattern_type == "gerundio"]),
            "anaphora_found": len([m for m in matches if m.pattern_type == "anáfora"]),
            "total_patterns_found": len(matches),
            "detection_latency_seconds": round(latency, 4)
        })

    return matches