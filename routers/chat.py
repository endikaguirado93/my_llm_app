from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from services.llm_service import run_completion

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class MessageEntry(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[MessageEntry]
    model: str = "llama3.2"

@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.post("/api/chat")
def chat(body: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    result = run_completion(messages, model=body.model)
    return {"response": result}