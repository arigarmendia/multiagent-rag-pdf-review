import pdfplumber
import mlflow
import time
from pydantic import BaseModel

CM_TO_PT = 28.35

MARGINS = {
    "top": 1.5 * CM_TO_PT,
    "bottom": 1.5 * CM_TO_PT,
    "inner": 2.0 * CM_TO_PT,
    "outer": 3.3 * CM_TO_PT,
}


class LayoutError(BaseModel):
    page_number: int
    error_type: str
    description: str
    element: str


@mlflow.trace(name="layout_analyzer")
def check_margins(pdf_path: str) -> list[LayoutError]:
    start_time = time.time()
    errors = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_number = i + 1
            page_width = page.width
            page_height = page.height

            content_left = MARGINS["inner"]
            content_right = page_width - MARGINS["outer"]
            content_top = MARGINS["top"]
            content_bottom = page_height - MARGINS["bottom"]

            for obj in page.objects.get("rect", []) + page.objects.get("figure", []):
                x0 = obj.get("x0", 0)
                x1 = obj.get("x1", 0)
                y0 = obj.get("y0", 0)
                y1 = obj.get("y1", 0)

                if x0 < content_left - 2.0 or x1 > content_right + 2.0:
                    errors.append(LayoutError(
                        page_number=page_number,
                        error_type="margen horizontal",
                        description=f"Elemento fuera del margen horizontal (x0={x0:.1f}, x1={x1:.1f}, permitido={content_left:.1f}-{content_right:.1f})",
                        element=obj.get("object_type", "elemento")
                    ))

                if y0 < content_top - 2.0 or y1 > content_bottom + 2.0:
                    errors.append(LayoutError(
                        page_number=page_number,
                        error_type="margen vertical",
                        description=f"Elemento fuera del margen vertical (y0={y0:.1f}, y1={y1:.1f}, permitido={content_top:.1f}-{content_bottom:.1f})",
                        element=obj.get("object_type", "elemento")
                    ))

    latency = time.time() - start_time

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "total_margin_errors": len(errors),
            "horizontal_errors": len([e for e in errors if e.error_type == "margen horizontal"]),
            "vertical_errors": len([e for e in errors if e.error_type == "margen vertical"]),
            "layout_latency_seconds": round(latency, 2)
        })

    return errors