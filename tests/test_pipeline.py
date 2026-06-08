from pipeline.processor import process_pdf
import fitz

def test_pipeline():
    src = fitz.open("data/sample_pdfs/test.pdf")
    doc = fitz.open()
    doc.insert_pdf(src, from_page=0, to_page=2)
    doc.save("data/sample_pdfs/test_3pages.pdf")
    src.close()
    doc.close()

    result = process_pdf("data/sample_pdfs/test_3pages.pdf")

    print(f"\nPDF: {result.pdf_path}")
    print(f"Páginas procesadas: {result.total_pages}")
    print(f"Total errores confirmados: {result.total_errors}")
    print(f"Tiempo total: {result.total_processing_time}s")
    print()

    for page in result.pages:
        print(f"--- Página {page.page_number} ({page.processing_time}s) ---")
        confirmed = [e for e in page.confirmed_errors if e.confirmed]
        if confirmed:
            for error in confirmed:
                print(f"  [{error.error_type}] {error.description}")
        else:
            print("  Sin errores confirmados")
        print()

    assert result.total_pages > 0