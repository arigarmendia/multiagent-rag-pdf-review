import mlflow
from security.guardrails_validator import validate_and_log_input, validate_and_log_output

@mlflow.trace(name="test_guardrails_input_clean")
def test_input_clean():
    result = validate_and_log_input(
        "El sistema fue implementado utilizando redes neuronales.",
        page_number=1
    )
    print(f"Output sanitizado: {result}")

@mlflow.trace(name="test_guardrails_input_pii")
def test_input_pii():
    result = validate_and_log_input(
        "Contactar a Juan Pérez en juan@email.com para más información.",
        page_number=1
    )
    print(f"Output sanitizado: {result}")

@mlflow.trace(name="test_guardrails_output_provenance")
def test_output_provenance():
    result = validate_and_log_output(
        output="La palabra 'metodo' debería ser 'método'.",
        sources=["El metodo utilizado fue validado por expertos."],
        agent_name="analyst",
        page_number=1
    )
    print(f"Output validado: {result}")