from agents.hermes_runner import run_hermes_text_task


def generate_report(
    analysis,
    extracted_data=None,
    save_result=None,
    source_info=None,
    classification=None,
    plan=None,
    feedback_path=None,
):
    if "error" in analysis:
        return "No data available for report"

    prompt = f"""
You are Hermes acting as the reporting agent for a CPA shipping-cost review pipeline.

Write a concise plain-text report for the user.

Include:
- source summary
- document classification
- extracted shipment details
- dedupe/db result
- historical average
- current shipment cost
- benchmark rate and benchmark source
- anomalies, if any
- a short conclusion focused on shipping-cost control

Use the following data:
source_info={source_info}
classification={classification}
plan={plan}
extracted_data={extracted_data}
save_result={save_result}
analysis={analysis}
feedback_path={feedback_path}
"""

    try:
        return run_hermes_text_task(prompt, timeout=300)
    except Exception:
        report = []
        if source_info:
            report.append(
                f"Source: {source_info.get('source_type', 'unknown')} | "
                f"{source_info.get('source_label', 'N/A')} | "
                f"File: {source_info.get('document_path', 'N/A')}"
            )
        if classification:
            report.append(
                f"Document Type: {classification.get('document_type', 'unknown')} | "
                f"Extractor: {classification.get('extractor_strategy', 'unknown')} | "
                f"Confidence: {classification.get('format_confidence', 'unknown')}"
            )
        if extracted_data:
            report.append(
                f"Shipment ID: {extracted_data.get('shipment_id') or 'N/A'} | "
                f"Origin: {extracted_data.get('origin') or 'N/A'} | "
                f"Destination: {extracted_data.get('destination') or 'N/A'} | "
                f"Cost: {extracted_data.get('cost') if extracted_data.get('cost') is not None else 'N/A'} | "
                f"Date: {extracted_data.get('date') or 'N/A'}"
            )
        if save_result:
            report.append(f"DB Status: {save_result.get('status', 'unknown')}")
        report.append(f"Historical Average Cost: {analysis['historical_average_cost']:.2f}")
        if analysis.get("current_cost") is not None:
            report.append(f"Current Shipment Cost: {analysis['current_cost']:.2f}")
        if analysis.get("market_rate") is not None:
            report.append(f"Benchmark Market Rate: {analysis['market_rate']:.2f}")
        if analysis.get("market_source"):
            report.append(
                f"Benchmark Source: {analysis['market_source']} | "
                f"Apify Actor Status: {analysis.get('apify_actor_status', 'unknown')} | "
                f"Live Apify Used: {analysis.get('used_live_apify', False)}"
            )
        if analysis["anomalies"]:
            report.append("Anomalies Detected:")
            for anomaly in analysis["anomalies"]:
                report.append(
                    f"- Shipment {anomaly['shipment_id']} cost {anomaly['cost']}"
                    f" (Market: {anomaly.get('market_rate', 'N/A')}) -> {anomaly.get('issue', '')}"
                )
        else:
            report.append("No anomalies detected")
        if feedback_path:
            report.append(f"Feedback Log: {feedback_path}")
        return "\n".join(report)
