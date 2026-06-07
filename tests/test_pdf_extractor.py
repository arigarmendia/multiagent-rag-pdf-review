from preprocessing.pdf_extractor import extract_pdf

def test_extract_pdf():
    pages = extract_pdf("data/sample_pdfs/test.pdf")
    
    assert len(pages) > 0
    assert pages[0].page_number == 1
    assert pages[0].text is not None
    assert pages[0].image_path is not None
    
    print(f"Páginas extraídas: {len(pages)}")
    print(f"Texto página 1 (primeros 200 chars): {pages[0].text[:200]}")