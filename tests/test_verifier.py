from agents.analyst import CandidateError
from agents.verifier import run_verifier

def test_verifier():
    candidates = [
        CandidateError(
            page_number=1,
            error_type="Uso incorrecto de gerundio",
            description="El gerundio 'logrando' expresa posterioridad",
            context="El sistema fue implementado logrando mejores resultados.",
            source="analyst"
        ),
        CandidateError(
            page_number=1,
            error_type="Uso de anáfora",
            description="El uso de 'El mismo' como anáfora puede ser incorrecto",
            context="El mismo fue probado en condiciones reales.",
            source="analyst"
        ),
        CandidateError(
            page_number=1,
            error_type="Falta de tilde",
            description="La palabra 'metodo' debería ser 'método'",
            context="El metodo utilizado fue validado por expertos.",
            source="analyst"
        ),
        CandidateError(
            page_number=1,
            error_type="Tilde incorrecta",
            description="La palabra 'imágen' lleva tilde incorrectamente, debe ser 'imagen'",
            context="Se muestra en la imágen siguiente.",
            source="analyst"
        ),
        CandidateError(
            page_number=5,
            error_type="tabla detectada",
            description="1 tabla detectada en la página — verificar caption y formato",
            context="Tabla sin caption visible",
            source="analyst"
        ),
    ]

    confirmed = run_verifier(candidates)

    print(f"Errores verificados: {len(confirmed)}")
    for error in confirmed:
        status = "✓ CONFIRMADO" if error.confirmed else "✗ DESCARTADO"
        print(f"{status} [{error.error_type}] Página {error.page_number}")
        print(f"  Razón: {error.reason}")
        print()