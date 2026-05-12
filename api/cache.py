import re
import threading
from datetime import datetime, timezone


def normalize_key(question: str, governing_body: str | None) -> str:
    normalized = re.sub(r'[^a-z0-9\s]', '', question.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return f"{normalized}|{governing_body or ''}"


def get_cached(db, key: str) -> dict | None:
    snap = db.collection("question_cache").document(key).get()
    if not snap.exists:
        return None
    threading.Thread(target=_record_hit, args=(db, key), daemon=True).start()
    return snap.to_dict()


def _record_hit(db, key: str) -> None:
    ref = db.collection("question_cache").document(key)
    snap = ref.get()
    if snap.exists:
        count = snap.to_dict().get("hit_count", 0)
        ref.update({
            "hit_count": count + 1,
            "last_hit_at": datetime.now(timezone.utc),
        })


def write_cache(
    db,
    key: str,
    question: str,
    governing_body: str | None,
    answer: str,
    sources: list[dict],
) -> None:
    db.collection("question_cache").document(key).set({
        "question": question,
        "governing_body": governing_body,
        "answer": answer,
        "sources": sources,
        "hit_count": 0,
        "created_at": datetime.now(timezone.utc),
        "last_hit_at": datetime.now(timezone.utc),
    })
