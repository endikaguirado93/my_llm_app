from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from routers import chat, calculator
from dotenv import load_dotenv
from db.database import engine, Base
from db import models  # noqa: F401 — ensures models are registered

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.include_router(chat.router)
app.include_router(calculator.router)

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})