from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes import expediente

app = FastAPI(title="ELECCIA")

app.include_router(expediente.router)


app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

templates = Jinja2Templates(directory="app/frontend/templates")


