from guardrails import Guard
from guardrails.hub import DetectPII

guard = Guard().use(
    DetectPII(
        pii_entities=["PERSON"],
        # language="en",
        on_fail="fix"
    )
)

text = "John Smith works at Stanford University."

result = guard.validate(text)

print(result.validation_passed)
print(result.error)
print(result.validated_output)
print(result.validation_summaries)