import fitz
from pathlib import Path
from pydantic import BaseModel


class PageContent(BaseModel):
    page_number: int
    text: str
    image_path: str | None = None

# Checks if there is a blank page
def is_blank_page(text: str, min_chars: int = 5) -> bool:
    return len(text.strip()) < min_chars

# Extracts text and images from a PDF, saves images in the "extracted" folder.
def extract_pdf(pdf_path: str, output_dir: str = "data/extracted") -> list[PageContent]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text()
        
        if is_blank_page(text):
            continue

        pix = page.get_pixmap(dpi=150)
        image_path = f"{output_dir}/page_{i+1}.png"
        pix.save(image_path)

        pages.append(PageContent(
            page_number=i + 1,
            text=text,
            image_path=image_path
        ))

    doc.close()
    return pages