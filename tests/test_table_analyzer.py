from preprocessing.table_analyzer import analyze_tables

def test_analyze_tables():
    image_path = "data/extracted/page_4.png"
    
    errors = analyze_tables(image_path, page_number=4)
    
    print(f"Errores de tablas encontrados: {len(errors)}")
    for error in errors:
        print(f"[{error.error_type}] Página {error.page_number}: {error.description}")