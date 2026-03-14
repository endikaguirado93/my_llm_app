from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from services.calculator_service import calculate

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class CalcRequest(BaseModel):
    expression: str

@router.get("/calculator")
def calculator_page(request: Request):
    return templates.TemplateResponse("calculator.html", {"request": request})

@router.post("/api/calculate")
def run_calculate(body: CalcRequest):
    result = calculate(body.expression)
    return {"result": result}