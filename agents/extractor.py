from agents.hermes_runner import run_hermes_json_task


def _to_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ("name", "value", "text", "city", "country", "address", "location"):
            nested = value.get(key)
            if isinstance(nested, (str, int, float)) and str(nested).strip():
                return str(nested).strip()
        flattened = [str(item).strip() for item in value.values() if str(item).strip()]
        return ", ".join(flattened) if flattened else None
    if isinstance(value, list):
        flattened = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(flattened) if flattened else None
    return str(value).strip() or None


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("amount", "value", "total", "price", "cost"):
            nested = value.get(key)
            if nested is not None:
                parsed = _to_number(nested)
                if parsed is not None:
                    return parsed
        return None
    if isinstance(value, list):
        for item in value:
            parsed = _to_number(item)
            if parsed is not None:
                return parsed
        return None
    cleaned = (
        str(value)
        .replace(",", "")
        .replace("$", "")
        .replace("£", "")
        .replace("€", "")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_data(text, classification=None, plan=None):
    classification = classification or {}
    plan = plan or {}
    required_fields = plan.get(
        "required_fields",
        ["shipment_id", "origin", "destination", "cost", "date"],
    )

    prompt = f"""
You are Hermes acting as the extraction agent in a shipping-cost pipeline.

Extract structured shipment information from the document text.

Return exactly one JSON object with these exact keys:
- shipment_id
- origin
- destination
- cost
- date

Context:
- document_type: {classification.get("document_type", "unknown")}
- extractor_strategy: {classification.get("extractor_strategy", "hermes_structured_extraction")}
- required_fields: {required_fields}

Rules:
- Use only information present in the document.
- `cost` must be a JSON number when possible.
- If a field is missing, set it to null.
- Return JSON only, with no markdown or explanation.

Document text:
{text[:16000]}
"""

    try:
        data = run_hermes_json_task(prompt, timeout=300)
        return {
            "shipment_id": _to_text(data.get("shipment_id")),
            "origin": _to_text(data.get("origin")),
            "destination": _to_text(data.get("destination")),
            "cost": _to_number(data.get("cost")),
            "date": _to_text(data.get("date")),
            "parser": "hermes_managed",
        }
    except Exception as exc:
        return {
            "error": "hermes extraction failed",
            "raw_output": str(exc),
        }
