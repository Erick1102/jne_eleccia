from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes import expediente_routes

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

# Incluir rutas de expedientes
app.include_router(expediente_routes.router)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")


