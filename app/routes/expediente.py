from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/expedientes", tags=["Expedientes"])
templates = Jinja2Templates(directory="app/frontend/templates")

@router.get("/")
async def index(request: Request):
    """Página principal donde el usuario ingresa un código de expediente"""
    return templates.TemplateResponse("index.html", {"request": request})


