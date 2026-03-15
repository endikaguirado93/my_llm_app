import time
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from services.llm_service import run_completion, run_arena_stream
from db.database import AsyncSessionLocal
from db.log_service import get_or_create_session, log_turn

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class MessageEntry(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[MessageEntry]
    model: str = "llama3.2"
    session_id: str | None = None  # ← client passes this after first turn

class ArenaRequest(BaseModel):
    messages: list

@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.post("/api/chat")
async def chat(body: ChatRequest):
    print(">>> /api/chat hit")
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    
    start = time.monotonic()
    error = None
    result = ""

    try:
        result = run_completion(messages, model=body.model)
    except Exception as e:
        error = str(e)
        raise
    finally:
        latency_ms = (time.monotonic() - start) * 1000
        async with AsyncSessionLocal() as db:
            session = await get_or_create_session(db, body.session_id)
            user_text = body.messages[-1].content if body.messages else ""
            await log_turn(
                db=db,
                session_id=session.id,
                model=body.model,
                user_message=user_text,
                assistant_message=result,
                latency_ms=latency_ms,
                error=error,
            )
            session_id = session.id

    return {"response": result, "session_id": session_id}


@router.post("/api/chat/arena/stream")
async def chat_arena_stream(req: ArenaRequest):
    result_data = {}
    model_times = {}

    async def logging_wrapper():
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        def run_generator():
            for chunk in run_arena_stream(req.messages):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        executor_task = loop.run_in_executor(None, run_generator)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break

            if '"type": "response"' in chunk:
                try:
                    payload = json.loads(chunk.replace("data: ", "").strip())
                    model_times[payload["model"]] = payload.get("response_time_ms")
                except Exception:
                    pass
            if '"type": "result"' in chunk:
                try:
                    payload = json.loads(chunk.replace("data: ", "").strip())
                    result_data.update(payload)
                except Exception:
                    pass
            yield chunk

        await executor_task

        # stream done — write to DB with per-model latency
        user_text = next(
            (m["content"] for m in reversed(req.messages) if m["role"] == "user"), ""
        )
        async with AsyncSessionLocal() as db:
            session = await get_or_create_session(db, None)
            for model, response_text in result_data.get("responses", {}).items():
                await log_turn(
                    db=db,
                    session_id=session.id,
                    model=model,
                    user_message=user_text,
                    assistant_message=response_text,
                    latency_ms=model_times.get(model),
                    error=None,
                )

    return StreamingResponse(
        logging_wrapper(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )