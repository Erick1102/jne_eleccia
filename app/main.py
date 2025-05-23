from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.routes import expediente_routes
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Crear instancia de FastAPI
app = FastAPI(title="Gestión de Expedientes", version="1.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar SessionMiddleware con opciones adicionales
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    session_cookie="eleccia_session",
    max_age=3600,  # 1 hora
    same_site="lax",
    https_only=False
)

# Incluir rutas de expedientes
app.include_router(expediente_routes.router)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")


