from preprocessing.layout_analyzer import check_margins

def test_check_margins():
    errors = check_margins("data/sample_pdfs/test.pdf")

    print(f"Total errores de márgenes: {len(errors)}")
    for error in errors[:5]:  # mostramos solo los primeros 5
        print(f"[{error.error_type}] Página {error.page_number}: {error.description}")

    assert isinstance(errors, list)