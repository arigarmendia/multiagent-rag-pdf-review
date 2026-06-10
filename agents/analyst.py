import json
import os
import time
from pydantic import BaseModel
from preprocessing.pattern_detector import PatternMatch
from preprocessing.layout_analyzer import LayoutError
from preprocessing.table_analyzer import TableError
from rag.retriever import retrieve
import mlflow
from pipeline.token_tracker import add
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url=os.getenv("VLLM_BASE_URL"),
    api_key="not-required"
)


class CandidateError(BaseModel):
    page_number: int
    error_type: str
    description: str
    context: str
    source: str


def build_prompt(
    patterns: list[PatternMatch],
    layout_errors: list[LayoutError],
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

    return f"""Sos un corrector de memorias académicas de posgrado en español.

Tu tarea es analizar ÚNICAMENTE los patrones detectados automáticamente. NO busques errores adicionales en el texto.

REGLAS LSE:
{rag_context}

PATRONES DETECTADOS:
{patterns_str}

ERRORES DE FORMATO:
{layout_str}

Si no hay patrones ni errores de formato, devolvé [].

Respondé SOLO con JSON:
[
  {{
    "error_type": "tipo",
    "description": "descripción concisa",
    "context": "fragmento exacto del texto"
  }}
]"""


@mlflow.trace(name="analyst")
def run_analyst(
    page_number: int,
    text: str,
    patterns: list[PatternMatch],
    layout_errors: list[LayoutError],
    table_errors: list[TableError],
) -> list[CandidateError]:

    # Generar errores de tabla directamente sin LLM
    results = []
    for table in table_errors:
        results.append(CandidateError(
            page_number=page_number,
            error_type=table.error_type,
            description=table.description,
            context=f"[tabla en página {page_number}]",
            source="analyst"
        ))

    # Si no hay patrones ni layout errors, devolver solo los errores de tabla
    if not patterns and not layout_errors:
        return results

    query_parts = list(set([p.pattern_type for p in patterns]))
    if layout_errors:
        query_parts.append("márgenes formato")
    for table in table_errors:
        if "margen" in table.error_type:
            query_parts.append("tabla fuera de margen")
        else:
            query_parts.append("tablas caption formato")

    query = " ".join(query_parts) if query_parts else "reglas generales escritura académica"
    print(f"RAG QUERY: {query}")

    rag_chunks = retrieve(query, k=3)
    rag_context = "\n\n".join([c.content for c in rag_chunks])

    prompt = build_prompt(page_number, text, patterns, layout_errors, rag_context)

    start_time = time.time()
    response = client.chat.completions.create(
        model=os.getenv("VLLM_MODEL", "qwen2.5-vl-32b"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000
    )
    latency = time.time() - start_time

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        llm_errors = json.loads(content)
    except json.JSONDecodeError:
        llm_errors = []

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "latency_seconds": round(latency, 2),
            "errors_found": len(llm_errors)
        })

    add(response.usage.prompt_tokens, response.usage.completion_tokens)

    # Combinar errores de tabla (directos) con errores del LLM (patrones)
    results.extend([
        CandidateError(
            page_number=page_number,
            error_type=e.get("error_type", ""),
            description=e.get("description", ""),
            context=e.get("context", "") if isinstance(e.get("context"), str) else "",
            source="analyst"
        )
        for e in llm_errors
    ])

    return results