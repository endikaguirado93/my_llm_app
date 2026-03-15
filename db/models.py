from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid, enum
from .database import Base

class Session(Base):
    __tablename__ = "sessions"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    messages   = relationship("Message", back_populates="session")
    logs       = relationship("RequestLog", back_populates="session")

class RoleEnum(str, enum.Enum):
    user      = "user"
    assistant = "assistant"

class Message(Base):
    __tablename__ = "messages"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role       = Column(Enum(RoleEnum))
    content    = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session    = relationship("Session", back_populates="messages")

class RequestLog(Base):
    __tablename__ = "request_logs"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    session_id      = Column(String, ForeignKey("sessions.id"))
    model           = Column(String)
    prompt_tokens   = Column(Integer, nullable=True)
    response_tokens = Column(Integer, nullable=True)
    latency_ms      = Column(Float, nullable=True)
    error           = Column(Text, nullable=True)   # NULL = success
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session         = relationship("Session", back_populates="logs")