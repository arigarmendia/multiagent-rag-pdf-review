import json
import os
import time
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel
from preprocessing.pattern_detector import PatternMatch
from preprocessing.layout_analyzer import LayoutError
from preprocessing.table_analyzer import TableError
from rag.retriever import retrieve
import mlflow

load_dotenv()

client = Groq(api_key=os.getenv("PLN3_GROQ_API_KEY"))


class CandidateError(BaseModel):
    page_number: int
    error_type: str
    description: str
    context: str
    source: str


def build_prompt(
    page_number: int,
    text: str,
    patterns: list[PatternMatch],
    layout_errors: list[LayoutError],
    table_errors: list[TableError],
    rag_context: str
) -> str:

    patterns_str = "\n".join([
        f"- [{p.pattern_type}] '{p.match}' → contexto: {p.context}"
        for p in patterns
    ]) or "Ninguno"

    layout_str = "\n".join([
        f"- [{e.error_type}] {e.description}"
        for e in layout_errors
    ]) or "Ninguno"

    table_str = "\n".join([
        f"- [{e.error_type}] {e.description}"
        for e in table_errors
    ]) or "Ninguno"

    return f"""Sos un corrector experto de memorias académicas de posgrado en español.

Analizá la siguiente información de la página {page_number} y determiná qué errores son reales según las reglas académicas del LSE-FIUBA.

REGLAS RELEVANTES DEL REGLAMENTO:
{rag_context}

PATRONES DETECTADOS AUTOMÁTICAMENTE:
{patterns_str}

ERRORES DE FORMATO (márgenes):
{layout_str}

TABLAS DETECTADAS:
{table_str}

TEXTO DE LA PÁGINA:
<texto>
{text[:1500]}
</texto>

Buscá específicamente estos tipos de errores:
1. Gerundios de posterioridad usados incorrectamente
2. Uso anafórico incorrecto de "el mismo/la misma", "el cual/la cual"
3. Palabras que deberían llevar tilde y no la tienen (ej: "metodo" → "método", "numero" → "número", "analisis" → "análisis", "automaticamente" → "automáticamente", "unicamente" → "únicamente")
4. Errores de formato y márgenes
5. Problemas con tablas

Respondé SOLO con una lista JSON con este formato exacto, sin texto adicional:
[
  {{
    "error_type": "tipo de error",
    "description": "descripción clara del error",
    "context": "fragmento donde aparece"
  }}
]

Si no hay errores reales respondé con: []"""

@mlflow.trace(name="analyst") # Using this decorator to automatically trace this function.
def run_analyst(
    page_number: int,
    text: str,
    patterns: list[PatternMatch],
    layout_errors: list[LayoutError],
    table_errors: list[TableError],
) -> list[CandidateError]:

    query_parts = [p.pattern_type for p in patterns]
    if layout_errors:
        query_parts.append("márgenes formato")
    if table_errors:
        query_parts.append("tablas caption formato")

    query = " ".join(query_parts) if query_parts else "reglas generales escritura académica"

    rag_chunks = retrieve(query, k=3)
    rag_context = "\n\n".join([c.content for c in rag_chunks])

    prompt = build_prompt(page_number, text, patterns, layout_errors, table_errors, rag_context)

    start_time = time.time()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000
    )
    latency = time.time() - start_time

    content = response.choices[0].message.content.strip()

    try:
        errors_raw = json.loads(content)
    except json.JSONDecodeError:
        errors_raw = []

    # Logs desired metrics in MLflow
    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "latency_seconds": round(latency, 2),
            "errors_found": len(errors_raw)
    })

    return [
        CandidateError(
            page_number=page_number,
            error_type=e.get("error_type", ""),
            description=e.get("description", ""),
            context=e.get("context", "") if isinstance(e.get("context"), str) else "",
            source="analyst"
        )
        for e in errors_raw
    ]