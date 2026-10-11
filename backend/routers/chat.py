from fastapi import APIRouter

from backend.schemas import ChatRequest, ChatResponse
from backend.services.rag import answer_question

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    return answer_question(payload.question)
