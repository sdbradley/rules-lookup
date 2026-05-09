import os
from contextlib import asynccontextmanager

import firebase_admin
import firebase_admin.credentials
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from auth import verify_token
from models import QueryRequest, QueryResponse
from query_handler import handle_query, stream_query
from rate_limit import check_rate_limit
from usage import get_monthly_count, increment_count, is_over_limit, is_subscriber
from webhook import handle_event, verify_webhook_secret

_db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "firebase-credentials.json")
    cred = firebase_admin.credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    from google.cloud import firestore
    _db = firestore.Client(project=os.environ["FIREBASE_PROJECT_ID"])
    yield


app = FastAPI(title="Rules Lookup API", lifespan=lifespan)


def get_db():
    return _db


def _check_limit(db, uid: str) -> None:
    if is_subscriber(db, uid):
        return
    count = get_monthly_count(db, uid)
    if is_over_limit(count):
        raise HTTPException(status_code=429, detail="Monthly query limit reached")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    authorization: str | None = Header(default=None),
):
    uid = verify_token(authorization)
    check_rate_limit(uid)
    db = get_db()
    _check_limit(db, uid)

    try:
        result = handle_query(req, uid=uid)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Query failed") from e

    increment_count(db, uid)
    return result


@app.post("/query/stream")
def query_stream(
    req: QueryRequest,
    authorization: str | None = Header(default=None),
):
    uid = verify_token(authorization)
    check_rate_limit(uid)
    db = get_db()
    _check_limit(db, uid)

    _, generator = stream_query(req, uid=uid)
    increment_count(db, uid)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.post("/webhooks/revenuecat")
async def revenuecat_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
):
    if not verify_webhook_secret(authorization):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    body = await request.json()
    event = body.get("event", {})
    handle_event(get_db(), event)
    return {"received": True}
