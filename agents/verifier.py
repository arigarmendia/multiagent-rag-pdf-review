import json
import os
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel
from agents.analyst import CandidateError
from rag.retriever import retrieve
import mlflow
import time
from pipeline.token_tracker import add
from openai import OpenAI

load_dotenv()

# client = Groq(api_key=os.getenv("PLN3_GROQ_API_KEY"))
client = OpenAI(
    base_url="http://192.168.1.217:8000/v1",
    api_key="not-required"
)


class ConfirmedError(BaseModel):
    page_number: int
    error_type: str
    description: str
    context: str
    confirmed: bool
    reason: str


@mlflow.trace(name="verifier") # Using this decorator to automatically trace this function.
def run_verifier(candidate_errors: list[CandidateError]) -> list[ConfirmedError]:
    if not candidate_errors:
        return []

    errors_str = "\n".join([
        f"- Página {e.page_number} [{e.error_type}]: {e.description} | Contexto: {e.context}"
        for e in candidate_errors
    ])

    # Recuperar reglas relevantes del RAG
    query = " ".join([e.error_type for e in candidate_errors])
    rag_chunks = retrieve(query, k=3)
    rag_context = "\n\n".join([c.content for c in rag_chunks])

    prompt = f"""Sos un verificador crítico de correcciones académicas en español.

El Agente Analista detectó los siguientes errores candidatos en una memoria de posgrado del LSE-FIUBA.
Tu tarea es revisar cada uno según las reglas ESPECÍFICAS del reglamento LSE, no según el español general.

REGLAS DEL REGLAMENTO LSE:
{rag_context}

ERRORES CANDIDATOS:
{errors_str}

Basándote ÚNICAMENTE en las reglas del reglamento LSE indicadas arriba, determiná si cada error es real o un falso positivo.

Respondé SOLO con una lista JSON con este formato exacto, sin texto adicional:
[
  {{
    "page_number": número de página,
    "error_type": "tipo de error",
    "description": "descripción del error",
    "context": "contexto donde aparece",
    "confirmed": true o false,
    "reason": "cita la regla específica del reglamento que justifica tu decisión"
  }}
]"""
    start_time = time.time()
    response = client.chat.completions.create(
        model="qwen2.5-vl-32b",
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
        errors_raw = json.loads(content)
    except json.JSONDecodeError:
        return []

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "latency_seconds": round(latency, 2),
            "errors_found": len(errors_raw)
    })
    # Custom function to track total tokens for each pipeline run
    add(response.usage.prompt_tokens, response.usage.completion_tokens)

    return [
        ConfirmedError(
            page_number=e.get("page_number", 0),
            error_type=e.get("error_type", ""),
            description=e.get("description", ""),
            context=e.get("context", "") if isinstance(e.get("context"), str) else "",
            confirmed=e.get("confirmed", False),
            reason=e.get("reason", "")
        )
        for e in errors_raw
    ]