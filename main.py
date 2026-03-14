from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from routers import chat, calculator
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.include_router(chat.router)
app.include_router(calculator.router)

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})