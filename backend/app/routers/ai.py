from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai import AIQueryRequest, AIQueryResponse
from app.services.ai_assistant import answer_with_llm_or_fallback

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/query", response_model=AIQueryResponse)
def ai_query(payload: AIQueryRequest, db: Session = Depends(get_db)):
    answer, intent, data = answer_with_llm_or_fallback(db, payload.query, payload.employee_email)
    return AIQueryResponse(answer=answer, intent=intent, data=data)
