from fastapi import APIRouter, Request, HTTPException, Query, Form
from fastapi.responses import HTMLResponse
import json

from app.config.cf_templates import templates  # Importar desde config
from app.libraries.lb_utils import validar_expediente, define_template
from app.libraries.lb_determina_estrategia import obtener_estrategia



router = APIRouter(tags=["Expedientes"])


@router.get("/")
async def expediente_view(request: Request):
    """Muestra la pantalla de ingreso del expediente"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/analiza_expediente", response_class=HTMLResponse)
async def procesar_expediente(request: Request, num_expediente: str = Form(...), tipo_expediente: int = Form(...), tipo_materia: int = Form(...)):
    """Ruta para analizar el expediente consultado"""

    # 1. valida si el expediente consultado pertenece al tipo de expediente y materia señalado
    if not validar_expediente(num_expediente, tipo_expediente, tipo_materia):
        raise HTTPException(status_code=400, detail="Expediente no válido para el tipo de materia")

    # 2. Obtenemos la estrategia adecuada según el tipo de materia
    estrategia = obtener_estrategia(tipo_expediente, tipo_materia)

    # 3. Llamamos al método procesar_expediente de la estrategia
    resultado, template_name = estrategia.procesar_expediente(num_expediente)
    if "error" in resultado:
        raise HTTPException(status_code=500, detail=resultado["error"])
    
    # 4. Identificar que template cargar basado en el tipo de expediente y materia de la estrategia utilizada
    #template_name = define_template(tipo_expediente, tipo_materia)   
    
    # 5. mostrar resultados del analisis realizado
    return templates.TemplateResponse(template_name, {"request": request, **resultado})

@router.get("/listado_procesados", response_class=HTMLResponse)
async def listado_procesados(request: Request):

    datos_listado = {
        "procesos": [
            {
                "expediente": "EX-2022-001",
                "tipo_proceso": "Inscripción de Lista",
                "estado": "En análisis",
                "fecha_creacion": "2022-01-15",
                "ultima_actualizacion": "2022-01-20"
            },
            {
                "expediente": "EX-2022-002",
                "tipo_proceso": "Apelación",
                "estado": "En revisión",
                "fecha_creacion": "2022-01-25",
                "ultima_actualizacion": "2022-01-28"
            },
            # Añadir más procesos según sea necesario
        ]
    }
    
    # Renderizar la plantilla con los datos
    return templates.TemplateResponse("listado_procesados.html", {"request": request, "datos_listado": datos_listado})

