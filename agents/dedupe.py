from doc_db.database import insert_shipment

def save_if_not_duplicate(data):
    if data.get("error"):
        return {"status": "error", "data": data}

    scalar_fields = ("shipment_id", "origin", "destination", "cost", "date")
    invalid_fields = [
        field for field in scalar_fields
        if isinstance(data.get(field), (dict, list, tuple, set))
    ]
    if invalid_fields:
        return {
            "status": "error",
            "data": data,
            "message": f"Invalid structured fields: {', '.join(invalid_fields)}",
        }

    result = insert_shipment(data)

    if result == 'Duplicate':
        return {"status": "duplicate", "data": data}
    
    return {"status": "saved", "data": data}
