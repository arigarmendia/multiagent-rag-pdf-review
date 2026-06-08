import fitz
import mlflow
import time
from pathlib import Path
from pydantic import BaseModel


class PageContent(BaseModel):
    page_number: int
    text: str
    image_path: str | None = None


def is_blank_page(text: str, min_chars: int = 5) -> bool:
    return len(text.strip()) < min_chars


@mlflow.trace(name="pdf_extractor")
def extract_pdf(pdf_path: str, output_dir: str = "data/extracted") -> list[PageContent]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    doc = fitz.open(pdf_path)
    pages = []
    blank_pages = 0

    for i, page in enumerate(doc):
        text = page.get_text()

        if is_blank_page(text):
            blank_pages += 1
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
    latency = time.time() - start_time

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "pages_extracted": len(pages),
            "blank_pages_filtered": blank_pages,
            "total_pages_in_pdf": len(pages) + blank_pages,
            "extraction_latency_seconds": round(latency, 2)
        })

    return pages