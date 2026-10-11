from fastapi import FastAPI

from backend.routers import chat, knowledge

app = FastAPI(title="Personal Knowledgebase AI", version="0.1.0")
app.include_router(knowledge.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
