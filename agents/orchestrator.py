from agents.hermes_runner import run_hermes_json_task


def _default_plan():
    return {
        "document_type": "shipping_document",
        "extractor_strategy": "hermes_structured_extraction",
        "format_confidence": "medium",
        "required_fields": ["shipment_id", "origin", "destination", "cost", "date"],
        "analysis_focus": "Compare shipment cost with benchmark market rate and historical average.",
        "report_focus": "Summarize extracted shipment details, benchmark comparison, and anomalies.",
    }


def build_execution_plan(source_info, document_path, text):
    prompt = f"""
You are Hermes coordinating a shipping-cost review pipeline.

Analyze the input source and document text, then return exactly one JSON object with these keys:
- document_type
- extractor_strategy
- format_confidence
- required_fields
- analysis_focus
- report_focus

Rules:
- `required_fields` must be a JSON array of strings.
- `analysis_focus` should be a short sentence.
- `report_focus` should be a short sentence.
- Keep `extractor_strategy` descriptive, such as `hermes_structured_extraction`.
- Return JSON only.
- Do not include markdown fences, explanations, or any text before or after the JSON object.

Source info:
- source_type: {source_info.get("source_type")}
- source_label: {source_info.get("source_label")}
- document_path: {document_path}

Document text:
{text[:12000]}
"""

    try:
        plan = run_hermes_json_task(prompt, timeout=300)
    except Exception:
        return _default_plan()

    default_plan = _default_plan()
    default_plan.update({key: value for key, value in plan.items() if value is not None})
    return default_plan
