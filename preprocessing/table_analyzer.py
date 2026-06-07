from pathlib import Path
from PIL import Image
from pydantic import BaseModel

_processor = None
_model = None


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


def analyze_tables(image_path: str, page_number: int) -> list[TableError]:
    import torch
    errors = []
    processor, model = get_model()
    
    image = Image.open(image_path).convert("RGB")
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
            tables_detected.append({
                "score": round(score.item(), 3),
                "box": [round(x, 1) for x in box.tolist()]
            })

    if tables_detected:
        errors.append(TableError(
            page_number=page_number,
            error_type="tabla detectada",
            description=f"{len(tables_detected)} tabla(s) detectada(s) en la página — verificar caption y formato"
        ))

    return errors