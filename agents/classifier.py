def classify_document(plan):
    return {
        "document_type": plan.get("document_type", "unknown"),
        "extractor_strategy": plan.get("extractor_strategy", "hermes_structured_extraction"),
        "format_confidence": plan.get("format_confidence", "unknown"),
    }
