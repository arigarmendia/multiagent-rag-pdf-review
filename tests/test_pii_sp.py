from guardrails import Guard
from guardrails.hub import DetectPII

guard = Guard().use(
    DetectPII(
        pii_entities=["PERSON"],
        language="es",
        on_fail="fix"
    )
)

text = "Juan Pérez trabaja en la Universidad de Buenos Aires."

result = guard.validate(text)

print(result.validation_passed)
print(result.error)
print(result.validated_output)
print(result)