from agents.market import get_market_rate
from doc_db.database import get_all_shipments


def _build_anomaly_list(shipments, market_rate):
    anomalies = []

    for shipment in shipments:
        if shipment.get("cost") is None:
            continue

        if shipment["cost"] > market_rate * 1.3:
            flagged = dict(shipment)
            flagged["market_rate"] = market_rate
            flagged["issue"] = "Above market rate"
            anomalies.append(flagged)

    return anomalies


def analyze_costs(current_shipment=None):
    historical_shipments = get_all_shipments()

    if not historical_shipments and not current_shipment:
        return {"error": "No data"}

    all_costs = [
        shipment["cost"]
        for shipment in historical_shipments
        if shipment.get("cost") is not None
    ]
    if current_shipment and current_shipment.get("cost") is not None:
        if not any(
            shipment.get("shipment_id") == current_shipment.get("shipment_id")
            for shipment in historical_shipments
        ):
            all_costs.append(current_shipment["cost"])

    if not all_costs:
        return {"error": "No shipment costs available"}

    market_result = get_market_rate(
        route=(current_shipment or {}).get("destination"),
        document_date=(current_shipment or {}).get("date"),
    )
    market_rate = market_result["rate"]
    anomaly_scope = [current_shipment] if current_shipment else historical_shipments

    return {
        "total_shipments": len(historical_shipments),
        "historical_average_cost": sum(all_costs) / len(all_costs),
        "current_cost": (current_shipment or {}).get("cost"),
        "market_rate": market_rate,
        "market_source": market_result.get("benchmark_source"),
        "apify_actor_status": market_result.get("apify_actor_status"),
        "used_live_apify": market_result.get("used_live_apify", False),
        "anomalies": _build_anomaly_list(anomaly_scope, market_rate),
    }
