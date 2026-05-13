from datetime import datetime, timezone


def write_feedback(db, uid: str, log_id: str, rating: str) -> None:
    doc_ref = db.collection("query_logs").document(log_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise ValueError(f"Log entry {log_id} not found")
    if doc.to_dict().get("uid") != uid:
        raise PermissionError("Access denied")
    doc_ref.update({
        "feedback": {
            "rating": rating,
            "created_at": datetime.now(timezone.utc),
        }
    })
