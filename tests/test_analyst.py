from agents.analyst import run_analyst
from preprocessing.pattern_detector import detect_patterns
from preprocessing.layout_analyzer import check_margins
from preprocessing.table_analyzer import analyze_tables

def test_analyst():
    text = """El sistema fue implementado logrando mejores resultados.
    El mismo fue probado en condiciones reales.
    Los datos fueron procesados automaticamente,permitiendo una mayor eficiencia.
    El metodo utilizado fue validado por expertos."""

    patterns = detect_patterns(text, page_number=1)
    layout_errors = []
    table_errors = []

    errors = run_analyst(
        page_number=1,
        text=text,
        patterns=patterns,
        layout_errors=layout_errors,
        table_errors=table_errors
    )

    print(f"Errores candidatos: {len(errors)}")
    for error in errors:
        print(f"[{error.error_type}] Página {error.page_number}: {error.description}")
        print(f"  Contexto: {error.context}")
        print()