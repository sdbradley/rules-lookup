import os

from fastapi import HTTPException
from firebase_admin import auth as firebase_auth

_SKIP_AUTH = os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes")


def verify_token(authorization: str | None) -> str:
    if _SKIP_AUTH:
        return "local-test-uid"
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    token = parts[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
