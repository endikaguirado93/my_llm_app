import time
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Session, Message, RequestLog, RoleEnum

async def get_or_create_session(db: AsyncSession, session_id: str | None) -> Session:
    if session_id:
        result = await db.get(Session, session_id)
        if result:
            return result
    new_session = Session()
    db.add(new_session)
    await db.flush()
    return new_session

async def log_turn(
    db: AsyncSession,
    session_id: str,
    model: str,
    user_message: str,
    assistant_message: str,
    latency_ms: float,
    prompt_tokens: int | None = None,
    response_tokens: int | None = None,
    error: str | None = None,
):
    db.add(Message(session_id=session_id, role=RoleEnum.user, content=user_message))
    db.add(Message(session_id=session_id, role=RoleEnum.assistant, content=assistant_message))
    db.add(RequestLog(
        session_id=session_id,
        model=model,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        latency_ms=latency_ms,
        error=error,
    ))
    await db.commit()