from datetime import datetime

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    governing_body: str | None = None
    conversation_id: str | None = None
    messages: list[dict] | None = None


class Source(BaseModel):
    governing_body: str
    rule_number: str | None = None
    section_title: str | None = None
    source_doc: str
    page_number: int | None = None


class ConversationSummary(BaseModel):
    id: str
    preview: str
    governing_body: str | None = None
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    preview: str
    governing_body: str | None = None
    created_at: datetime
    messages: list[dict]


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    conversation_id: str | None = None
    log_id: str | None = None
    cache_bypass: bool = False


class FeedbackRequest(BaseModel):
    log_id: str
    rating: str
