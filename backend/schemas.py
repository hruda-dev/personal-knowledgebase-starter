from pydantic import BaseModel, Field


class TextKnowledgeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    index: int
    filename: str
    page: int | None = None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
