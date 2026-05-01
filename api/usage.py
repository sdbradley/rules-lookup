from datetime import datetime, timezone

FREE_TIER_LIMIT = 20


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _doc_ref(db, uid: str):
    return db.collection("usage").document(f"{uid}_{_month_key()}")


def get_monthly_count(db, uid: str) -> int:
    snap = _doc_ref(db, uid).get()
    if not snap.exists:
        return 0
    return snap.to_dict().get("count", 0)


def increment_count(db, uid: str) -> None:
    ref = _doc_ref(db, uid)
    snap = ref.get()
    current = snap.to_dict().get("count", 0) if snap.exists else 0
    ref.set({"uid": uid, "month": _month_key(), "count": current + 1})


def is_over_limit(count: int) -> bool:
    return count >= FREE_TIER_LIMIT
