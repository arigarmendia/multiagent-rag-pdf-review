from pipeline.processor import process_pdf

def test_pipeline():
    from preprocessing.pdf_extractor import extract_pdf
    
    # Solo procesamos 2 páginas para el test
    result = process_pdf("data/sample_pdfs/test.pdf")

    print(f"\nPDF: {result.pdf_path}")
    print(f"Páginas procesadas: {result.total_pages}")
    print(f"Total errores confirmados: {result.total_errors}")
    print(f"Tiempo total: {result.total_processing_time}s")
    print()

    for page in result.pages[:2]:
        print(f"--- Página {page.page_number} ({page.processing_time}s) ---")
        confirmed = [e for e in page.confirmed_errors if e.confirmed]
        if confirmed:
            for error in confirmed:
                print(f"  [{error.error_type}] {error.description}")
        else:
            print("  Sin errores confirmados")
        print()

    assert result.total_pages > 0