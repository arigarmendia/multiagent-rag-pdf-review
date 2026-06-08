import mlflow
from guardrails import Guard
from guardrails.hub import GibberishText, SecretsPresent, ProvenanceLLM
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://192.168.1.217:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "qwen2.5-vl-32b")


def get_llm_callable():
    client = OpenAI(base_url=VLLM_BASE_URL, api_key="dummy")

    def llm_callable(prompt: str) -> str:
        response = client.chat.completions.create(
            model=VLLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200
        )
        return response.choices[0].message.content

    return llm_callable


def validate_and_log_input(text: str, page_number: int) -> str:
    guard = Guard().use(
        # DetectPII desactivado — no soporta español correctamente
        # DetectPII(
        #     pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "LOCATION", "DATE_TIME", "NRP", "ID"],
        #     on_fail="noop",
        #     language="es"
        # )
        SecretsPresent(on_fail="noop")
    ).use(
        GibberishText(threshold=0.5, on_fail="noop")
    )

    result = guard.validate(text)

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            f"page_{page_number}_input_validation_passed": result.validation_passed,
            f"page_{page_number}_input_findings": str(result.error) if result.error else "none",
            f"page_{page_number}_input_was_sanitized": text != result.validated_output,
        })

    return result.validated_output or text


def validate_and_log_output(output: str, sources: list[str], agent_name: int, page_number: int) -> str:
    guard = Guard().use(
        ProvenanceLLM(
            llm_callable=get_llm_callable(),
            on_fail="filter"
        )
    )

    result = guard.validate(output, metadata={"sources": sources})

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            f"page_{page_number}_{agent_name}_output_validation_passed": result.validation_passed,
            f"page_{page_number}_{agent_name}_output_findings": str(result.error) if result.error else "none",
            f"page_{page_number}_{agent_name}_output_was_filtered": output != result.validated_output,
        })

    return result.validated_output or output