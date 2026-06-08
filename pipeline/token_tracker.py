_counts = {"prompt": 0, "completion": 0}


def reset():
    _counts["prompt"] = 0
    _counts["completion"] = 0


def add(prompt_tokens: int, completion_tokens: int):
    _counts["prompt"] += prompt_tokens
    _counts["completion"] += completion_tokens


def get():
    return {
        "pipeline_prompt_tokens": _counts["prompt"],
        "pipeline_completion_tokens": _counts["completion"],
        "pipeline_total_tokens": _counts["prompt"] + _counts["completion"]
    }