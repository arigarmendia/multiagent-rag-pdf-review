from pathlib import Path
from PIL import Image
from pydantic import BaseModel
import mlflow
import time

_processor = None
_model = None

CM_TO_PT = 28.35
MARGINS = {
    "inner": 2.0 * CM_TO_PT,
    "outer": 3.3 * CM_TO_PT,
}


def get_model():
    global _processor, _model
    if _processor is None or _model is None:
        from transformers import AutoImageProcessor, TableTransformerForObjectDetection
        _processor = AutoImageProcessor.from_pretrained(
            "microsoft/table-transformer-detection",
            local_files_only=True
        )
        _model = TableTransformerForObjectDetection.from_pretrained(
            "microsoft/table-transformer-detection",
            local_files_only=True
        )
    return _processor, _model


class TableError(BaseModel):
    page_number: int
    error_type: str
    description: str


@mlflow.trace(name="table_analyzer")
def analyze_tables(image_path: str, page_number: int, page_width_pt: float = 595.276) -> list[TableError]:
    import torch
    start_time = time.time()
    errors = []
    processor, model = get_model()

    image = Image.open(image_path).convert("RGB")
    img_width_px = image.size[0]

    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]])
    results = processor.post_process_object_detection(
        outputs, threshold=0.7, target_sizes=target_sizes
    )[0]

    tables_detected = []
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        if model.config.id2label[label.item()] == "table":
            box_px = [round(x, 1) for x in box.tolist()]

            scale = page_width_pt / img_width_px
            x0_pt = box_px[0] * scale
            x1_pt = box_px[2] * scale

            tables_detected.append({
                "score": round(score.item(), 3),
                "box_px": box_px,
                "x0_pt": x0_pt,
                "x1_pt": x1_pt
            })

            content_left = MARGINS["inner"]
            content_right = page_width_pt - MARGINS["outer"]

            if x0_pt < content_left - 2.0 or x1_pt > content_right + 2.0:
                errors.append(TableError(
                    page_number=page_number,
                    error_type="tabla fuera de margen",
                    description=f"Tabla fuera del margen horizontal (x0={x0_pt:.1f}pt, x1={x1_pt:.1f}pt, permitido={content_left:.1f}-{content_right:.1f}pt)"
                ))
            else:
                errors.append(TableError(
                    page_number=page_number,
                    error_type="tabla detectada",
                    description="Tabla detectada — verificar caption y formato"
                ))

    latency = time.time() - start_time

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "page_number": page_number,
            "tables_detected": len(tables_detected),
            "inference_latency_seconds": round(latency, 2),
            "detection_threshold": 0.7
        })

    return errors