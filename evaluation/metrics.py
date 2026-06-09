import json
from pathlib import Path


def load_ground_truth(gt_path: str = "data/ground_truth/ground_truth.json") -> dict:
    with open(gt_path) as f:
        return json.load(f)


def calculate_metrics(pdf_name: str, confirmed_errors: list, gt_path: str = "data/ground_truth/ground_truth.json") -> dict:
    gt = load_ground_truth(gt_path)
    
    pdf_key = Path(pdf_name).name
    if pdf_key not in gt:
        return {"precision": None, "recall": None, "f1": None, "note": "Sin ground truth para este documento"}

    ground_truth = gt[pdf_key]
    total_gt = len(ground_truth)
    total_predicted = len([e for e in confirmed_errors if e.confirmed])

    # True positives — errores confirmados que matchean el ground truth por página y tipo
    true_positives = 0
    for e in confirmed_errors:
        if not e.confirmed:
            continue
        for gt_error in ground_truth:
            if e.page_number == gt_error["page"]:
                if gt_error["error_type"].lower() in e.error_type.lower():
                    true_positives += 1
                    break

    precision = round(true_positives / total_predicted, 3) if total_predicted > 0 else 0
    recall = round(true_positives / total_gt, 3) if total_gt > 0 else 0
    f1 = round(2 * precision * recall / (precision + recall), 3) if (precision + recall) > 0 else 0

    return {
        "true_positives": true_positives,
        "total_predicted": total_predicted,
        "total_ground_truth": total_gt,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }