from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    governing_body: str | None = None


class Source(BaseModel):
    governing_body: str
    rule_number: str | None = None
    section_title: str | None = None
    source_doc: str
    page_number: int | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
