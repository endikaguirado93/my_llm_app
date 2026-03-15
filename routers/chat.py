from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.llm_service import run_completion, run_arena_stream

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class MessageEntry(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[MessageEntry]
    model: str = "llama3.2"

class ArenaRequest(BaseModel):      # ← must exist before it's used below
    messages: list

@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.post("/api/chat")
def chat(body: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    result = run_completion(messages, model=body.model)
    return {"response": result}


@router.post("/api/chat/arena/stream")
def chat_arena_stream(req: ArenaRequest):
    return StreamingResponse(
        run_arena_stream(req.messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )