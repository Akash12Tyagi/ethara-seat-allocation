from pydantic import BaseModel


class AIQueryRequest(BaseModel):
    query: str
    employee_email: str | None = None  # optional context, e.g. "who am I" queries


class AIQueryResponse(BaseModel):
    answer: str
    intent: str
    data: dict | None = None
