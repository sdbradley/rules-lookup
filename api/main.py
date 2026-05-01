import os
from contextlib import asynccontextmanager

import firebase_admin
import firebase_admin.credentials
from fastapi import FastAPI, Header, HTTPException

from auth import verify_token
from models import QueryRequest, QueryResponse
from query_handler import handle_query
from usage import get_monthly_count, increment_count, is_over_limit

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    authorization: str | None = Header(default=None),
):
    uid = verify_token(authorization)

    db = get_db()
    count = get_monthly_count(db, uid)
    if is_over_limit(count):
        raise HTTPException(status_code=429, detail="Monthly query limit reached")

    try:
        result = handle_query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Query failed") from e

    increment_count(db, uid)
    return result
