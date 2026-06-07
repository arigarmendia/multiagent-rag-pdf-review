import pdfplumber
from pydantic import BaseModel

# Márgenes definidos en MastersDoctoralThesis.cls (en puntos PDF)
# 1 cm = 28.35 puntos
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


def check_margins(pdf_path: str) -> list[LayoutError]:
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

                if x0 < content_left or x1 > content_right:
                    errors.append(LayoutError(
                        page_number=page_number,
                        error_type="margen horizontal",
                        description=f"Elemento fuera del margen horizontal (x0={x0:.1f}, x1={x1:.1f}, permitido={content_left:.1f}-{content_right:.1f})",
                        element=obj.get("object_type", "elemento")
                    ))

                if y0 < content_top or y1 > content_bottom:
                    errors.append(LayoutError(
                        page_number=page_number,
                        error_type="margen vertical",
                        description=f"Elemento fuera del margen vertical (y0={y0:.1f}, y1={y1:.1f}, permitido={content_top:.1f}-{content_bottom:.1f})",
                        element=obj.get("object_type", "elemento")
                    ))

    return errors