import uuid
from datetime import datetime, timezone

from google.cloud import firestore


def create_conversation(db, uid: str, governing_body: str | None, preview: str) -> str:
    conv_id = str(uuid.uuid4())
    db.collection("users").document(uid).collection("conversations").document(conv_id).set({
        "created_at": datetime.now(timezone.utc),
        "governing_body": governing_body,
        "preview": preview[:100],
    })
    return conv_id


def append_message(
    db,
    uid: str,
    conversation_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> None:
    data: dict = {
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc),
    }
    if sources is not None:
        data["sources"] = sources
    db.collection("users").document(uid).collection("conversations").document(
        conversation_id
    ).collection("messages").add(data)


def list_conversations(db, uid: str, limit: int = 50) -> list[dict]:
    docs = (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    return result


def get_messages(db, uid: str, conversation_id: str) -> list[dict]:
    docs = (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
        .collection("messages")
        .order_by("created_at")
        .stream()
    )
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    return result
