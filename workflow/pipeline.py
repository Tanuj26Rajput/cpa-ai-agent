from agents.analyzer import analyze_costs
from agents.classifier import classify_document
from agents.dedupe import save_if_not_duplicate
from agents.extractor import extract_data
from agents.feedback import record_feedback
from agents.loader import load_document
from agents.orchestrator import build_execution_plan
from agents.report import generate_report
from agents.source import resolve_input
from doc_db.database import init_db


def run_pipeline(input_location=None, source_type="local"):
    init_db()

    source_info = resolve_input(source_type=source_type, location=input_location)
    document_path = source_info["document_path"]

    text = load_document(document_path)
    plan = build_execution_plan(source_info, document_path, text)
    classification = classify_document(plan)

    data = extract_data(text, classification=classification, plan=plan)
    if data.get("error"):
        feedback_path = record_feedback(
            {
                "status": "extraction_failed",
                "source_type": source_info["source_type"],
                "document_path": str(document_path),
                "plan": plan,
                "classification": classification,
                "error": data["raw_output"],
            }
        )
        return f"Extraction failed: {data['raw_output']}\nFeedback Log: {feedback_path}"

    save_result = save_if_not_duplicate(data)
    analysis = analyze_costs(current_shipment=data)
    feedback_path = record_feedback(
        {
            "status": "completed",
            "source_type": source_info["source_type"],
            "document_path": str(document_path),
            "plan": plan,
            "classification": classification,
            "extracted_data": data,
            "save_status": save_result["status"],
            "market_source": analysis.get("market_source"),
            "used_live_apify": analysis.get("used_live_apify"),
            "anomalies": analysis.get("anomalies", []),
        }
    )

    return generate_report(
        analysis,
        extracted_data=data,
        save_result=save_result,
        source_info={**source_info, "document_path": str(document_path)},
        classification=classification,
        plan=plan,
        feedback_path=feedback_path,
    )
