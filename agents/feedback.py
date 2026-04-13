import json
from datetime import datetime, UTC
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = PROJECT_ROOT / ".hermes-runtime" / "feedback" / "pipeline_feedback.jsonl"


def record_feedback(entry):
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **entry,
    }
    with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return FEEDBACK_PATH
