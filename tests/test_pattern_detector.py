from preprocessing.pattern_detector import detect_patterns

def test_detect_patterns():
    text = """El sistema fue implementado logrando mejores resultados.
    El mismo fue probado en condiciones reales.
    Los datos fueron procesados permitiendo una mayor eficiencia,
    el cual fue validado por expertos."""

    matches = detect_patterns(text, page_number=1)

    assert len(matches) > 0

    for match in matches:
        print(f"[{match.pattern_type}] '{match.match}'")
        print(f"  Contexto: {match.context}")
        print()

    print(f"Total matches: {len(matches)}")