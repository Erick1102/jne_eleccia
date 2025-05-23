from fastapi import APIRouter, Request, HTTPException, Query, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from datetime import datetime
import os
import asyncio
from functools import wraps
import jwt
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from app.database.db_session import get_db
from app.database.models.db_models_eleccia import Expediente, TipoExpediente, Materia, Estado, Resolucion, EstadoRequisitoExpediente, ConfiguracionRequisito
from app.config.cf_templates import templates
from app.libraries.lb_utils import validar_expediente, actualizar_estado_requisito
from app.libraries.lb_determina_estrategia import obtener_estrategia
from app.services.sr_ia_services import generar_resolucion_ia, calificacion_resolucion, obtener_normativas
from app.config.cf_constantes import BASE_PATH_DOCUMENTOS
import markdown as md
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

router = APIRouter(tags=["Expedientes"])
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Función para verificar el token JWT
def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Verificar que el token tenga la estructura correcta
        required_fields = ['unique_name', 'idexpediente', 'idusuario', 'exp']
        if not all(field in payload for field in required_fields):
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

# Decorador login_required
def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = request.session.get("user")
        if not user:
            return RedirectResponse(url="https://sije.jne.gob.pe", status_code=302)
        return await func(request, *args, **kwargs)
    return wrapper

# Dependencia para verificar el token y almacenar el usuario "en sesión"
async def token_required(request: Request, token: str = Query(...)):
    payload = verify_access_token(token)
    if not payload:
        return templates.TemplateResponse(
            "views/error.html",
            {
                "request": request,
                "error_message": "Token inválido o expirado. Por favor, verifique su token de acceso e intente nuevamente."
            }
        )
    request.session["user"] = payload['unique_name']
    request.session["idexpediente"] = payload['idexpediente']
    return payload

# Ruta protegida por el token
@router.get("/valida")
async def valida(request: Request, payload: dict = Depends(token_required), db: Session = Depends(get_db)):
    # Si el payload es una respuesta de plantilla, la devolvemos directamente
    if hasattr(payload, 'template'):
        return payload

    try:
        # Obtener el expediente de la base de datos usando el idexpediente del token
        expediente = await asyncio.to_thread(
            lambda: db.query(Expediente).filter(
                Expediente.numero_expediente == payload['idexpediente']
            ).first()
        )
        
        if not expediente:
            return templates.TemplateResponse(
                "views/error.html", 
                {
                    "request": request,
                    "error_message": "Expediente no encontrado en el sistema ELECCIA"
                }
            )
            
        return RedirectResponse(
            url=f"/ver_analisis_expediente?id_expediente={expediente.id_expediente}",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
            "views/error.html", 
            {
                "request": request,
                "error_message": f"Error al procesar la solicitud: {str(e)}"
            }
        )

@router.get("/")
async def expediente_view(request: Request):
    """Muestra la pantalla de ingreso del expediente"""
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/analiza_expediente", response_class=HTMLResponse)
async def analiza_expediente(request: Request, num_expediente: str = Form(...), tipo_expediente: int = Form(...), tipo_materia: int = Form(...)):
    """Ruta para analizar el expediente consultado"""

    # 1. valida si el expediente consultado pertenece al tipo de expediente y materia señalado
    es_valido = await asyncio.to_thread(validar_expediente, num_expediente, tipo_expediente, tipo_materia)
    if not es_valido:
        raise HTTPException(status_code=400, detail="Expediente no válido para el tipo de materia")

    # 2. Obtenemos la estrategia adecuada según el tipo de expediente y materia
    estrategia = await asyncio.to_thread(obtener_estrategia, tipo_expediente, tipo_materia)

    # 3. Llamamos al método procesar_expediente de la estrategia
    resultado, template_name = await asyncio.to_thread(estrategia.procesar_expediente, num_expediente)
    if "error" in resultado:
        raise HTTPException(status_code=500, detail=resultado["error"])
       
    # 5. mostrar resultados del analisis realizado
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return RedirectResponse(url=f"/listado_procesados?t={timestamp}", status_code=303)

@router.get("/listado_procesados", response_class=HTMLResponse)
async def listado_procesados(
    request: Request,
    num_expediente: str = Query(None),
    tipo_proceso: str = Query(None),
    materia: str = Query(None),
    fecha_desde: str = Query(None),
    fecha_hasta: str = Query(None),
    estado: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Construir la consulta base
    query = db.query(
        Expediente.id_expediente,
        Expediente.numero_expediente,
        Expediente.nombre_expediente,
        TipoExpediente.codigo_tipo_expediente.label('tipo_expediente'),
        Materia.codigo_materia.label('materia'),
        Estado.codigo_estado.label('estado'),
        Expediente.usuario_asignado,
        Expediente.creado_en,
        Resolucion.archivo_resolucion
    ).join(
        TipoExpediente, Expediente.id_tipo_expediente == TipoExpediente.id_tipo_expediente
    ).join(
        Materia, Expediente.id_materia == Materia.id_materia
    ).join(
        Estado, Expediente.id_estado == Estado.id_estado
    ).outerjoin(
        Resolucion, 
        and_(
            Expediente.id_expediente == Resolucion.id_expediente,
            Resolucion.fecha_modificacion == (
                db.query(func.max(Resolucion.fecha_modificacion))
                .filter(Resolucion.id_expediente == Expediente.id_expediente)
                .correlate(Expediente)
                .scalar_subquery()
            )
        )
    )

    # Aplicar filtros solo si tienen valor
    if num_expediente and num_expediente != "None":
        query = query.filter(Expediente.numero_expediente.ilike(f"%{num_expediente}%"))
    
    if tipo_proceso and tipo_proceso != "None":
        query = query.filter(TipoExpediente.codigo_tipo_expediente == tipo_proceso)
    
    if materia and materia != "None":
        query = query.filter(Materia.codigo_materia == materia)
    
    if fecha_desde and fecha_desde != "None":
        fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        query = query.filter(Expediente.creado_en >= fecha_desde_dt)
    
    if fecha_hasta and fecha_hasta != "None":
        fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        query = query.filter(Expediente.creado_en <= fecha_hasta_dt)
    
    if estado and estado != "None":
        query = query.filter(Estado.codigo_estado == estado)

    # PAGINACION
    total_records = await asyncio.to_thread(query.count)
    total_pages = (total_records + per_page - 1) // per_page
    page = min(page, total_pages) if total_pages > 0 else 1
    offset = (page - 1) * per_page
    query = query.order_by(Expediente.creado_en.desc()).offset(offset).limit(per_page)

    # Ejecutar la consulta
    expedientes = await asyncio.to_thread(query.all)

    # Convertir los resultados a un formato adecuado para la plantilla
    datos_listado = {
        "procesos": [
            {
                "id_expediente": exp.id_expediente,
                "expediente": exp.numero_expediente,
                "nombre_expediente": exp.nombre_expediente,
                "tipo_proceso": exp.tipo_expediente,
                "materia": exp.materia,
                "estado": exp.estado,
                "fecha_creacion": exp.creado_en.strftime("%Y-%m-%d") if exp.creado_en else "",
                "usuario": exp.usuario_asignado,
                "archivo_resolucion": exp.archivo_resolucion
            }
            for exp in expedientes
        ],
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_records": total_records,
            "per_page": per_page,
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
    }
    
    # Renderizar la plantilla con los datos
    response = templates.TemplateResponse("listado_procesados.html", {
        "request": request, 
        "datos_listado": datos_listado,
        "filtros": {
            "num_expediente": num_expediente if num_expediente != "None" else "",
            "tipo_proceso": tipo_proceso if tipo_proceso != "None" else "",
            "materia": materia if materia != "None" else "",
            "fecha_desde": fecha_desde if fecha_desde != "None" else "",
            "fecha_hasta": fecha_hasta if fecha_hasta != "None" else "",
            "estado": estado if estado != "None" else ""
        }
    })
    
    # Agregar headers para evitar caché
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

@router.get("/ver_analisis_expediente", response_class=HTMLResponse)
async def ver_analisis_expediente(request: Request, id_expediente: int, db: Session = Depends(get_db)):
    """Muestra el análisis de un expediente específico"""
    
    # Obtener la información del expediente con sus relaciones
    expediente = await asyncio.to_thread(
        lambda: db.query(Expediente).options(
            joinedload(Expediente.tipo_expediente),
            joinedload(Expediente.materia)
        ).filter(Expediente.id_expediente == id_expediente).first()
    )
    
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    # Cambiar estado de "PENDIENTE" a "EN_PROCESO"
    if expediente.id_estado == 3:
        expediente.id_estado = 4
        expediente.modificado_por = "ELECCIA"
        expediente.modificado_en = func.current_timestamp()
        await asyncio.to_thread(db.commit)
    
    # Obtener la última resolución del expediente
    resolucion = await asyncio.to_thread(
        lambda: db.query(Resolucion).filter(
            Resolucion.id_expediente == id_expediente
        ).order_by(Resolucion.fecha_creacion.desc()).first()
    )
    
    if not resolucion:
        raise HTTPException(status_code=404, detail="No se encontró resolución para este expediente")
    
    # Obtener los requisitos del expediente
    requisitos_expediente = await asyncio.to_thread(
        lambda: db.query(EstadoRequisitoExpediente).filter(
            EstadoRequisitoExpediente.id_expediente == id_expediente
        ).all()
    )
    
    # Construir tab_solicitud_lista (requisitos LISTA)
    tab_solicitud_lista = {
        "id": "solicitud",
        "nombre": "Solicitud de Inscripción",
        "requisitos": []
    }
    
    # Construir tab_acta_eleccion_interna (requisitos ACTA)
    tab_acta_eleccion_interna = {
        "id": "acta_eleccion_interna",
        "nombre": "Acta de Elección Interna",
        "requisitos": []
    }
    
    # Construir tab_hoja_vida_candidatos (requisitos CANDIDATO)
    tab_hoja_vida_candidatos = {
        "id": "hoja_vida_candidatos",
        "nombre": "Hoja de Vida de Candidatos",
        "candidatos": []
    }
    
    # Construir tab_plan_gobierno (requisitos PLAN_GOB)
    tab_plan_gobierno = {
        "id": "plan_gobierno",
        "nombre": "Plan de Gobierno",
        "requisitos": []
    }
    
    # Diccionario para agrupar requisitos por candidato
    candidatos_requisitos = {}
    
    # Procesar cada requisito según su tipo
    for req in requisitos_expediente:
        # Determinar el estado y color según el id_estado_validacion
        if req.id_estado_validacion == 7:
            estado_texto = "Cumple"
            estado_color = "green"
            estado = "CUMPLE"
        elif req.id_estado_validacion == 10:
            estado_texto = "Alerta"
            estado_color = "amber"
            estado = "ALERTA"
        else:
            estado_texto = "No Cumple"
            estado_color = "red"
            estado = "NO_CUMPLE"
        
        # Determinar el método de validación basado en el validador
        metodo_validacion = f"Validado por {req.validado_por}" if req.validado_por else "Verificado por Eleccia"
        
        requisito_info = {
            "id_estado_requisito": req.id_estado_requisito,
            "nombre": req.configuracion.requisito.nombre_requisito,
            "descripcion": req.configuracion.requisito.descripcion,
            "observacion": req.observaciones or "Validación pendiente",
            "estado": estado,
            "estado_color": estado_color,
            "estado_texto": estado_texto,
            "metodo_validacion": metodo_validacion,
            "boton_accion": req.archivo_ruta or ""
        }
        
        if req.tipo_requisito == "LISTA":
            tab_solicitud_lista["requisitos"].append(requisito_info)
        elif req.tipo_requisito == "ACTA":
            tab_acta_eleccion_interna["requisitos"].append(requisito_info)
        elif req.tipo_requisito == "PLAN_GOB":
            tab_plan_gobierno["requisitos"].append(requisito_info)
        elif req.tipo_requisito == "CANDIDATO":
            # Agrupar requisitos por candidato
            candidato = req.candidato
            
            # Si el candidato no existe, usar un identificador temporal
            if candidato is None:
                candidato_key = f"temp_{req.id_estado_requisito}"
            else:
                candidato_key = candidato.dni
            
            # Inicializar el candidato si no existe
            if candidato_key not in candidatos_requisitos:
                if candidato is None:
                    candidatos_requisitos[candidato_key] = {
                        "dni": "No disponible",
                        "nombres": "Candidato no encontrado",
                        "apellidos": "",
                        "cargo": "No disponible",
                        "requisitos": []
                    }
                else:
                    candidatos_requisitos[candidato_key] = {
                        "dni": candidato.dni,
                        "nombres": candidato.nombres,
                        "apellidos": candidato.apellidos,
                        "cargo": candidato.puesto_postula,
                        "requisitos": []
                    }
            
            # Agregar el requisito a la lista de requisitos del candidato
            candidatos_requisitos[candidato_key]["requisitos"].append(requisito_info)
    
    # Procesar los candidatos y determinar si cumplen todos los requisitos
    for candidato_key, candidato_data in candidatos_requisitos.items():
        # Un candidato cumple solo si todos sus requisitos cumplen
        todos_cumplen = all(req["estado"] == "CUMPLE" for req in candidato_data["requisitos"])
        candidato_data["cumple"] = todos_cumplen
        
        # Agregar el candidato al tab
        tab_hoja_vida_candidatos["candidatos"].append(candidato_data)
    
    # Construir el resumen_analisis
    resumen_analisis = {
        "analisis_realizado": True,
        "total_requisitos": resolucion.total_requisitos,
        "requisitos_cumplidos": resolucion.requisitos_cumplidos,
        "requisitos_faltantes": resolucion.requisitos_faltantes,
        "porcentaje_cumplimiento": round((resolucion.requisitos_cumplidos / resolucion.total_requisitos * 100) if resolucion.total_requisitos > 0 else 0, 2),
        "mensaje_alerta": f"Faltan {resolucion.requisitos_faltantes} requisitos por cumplir." if resolucion.requisitos_faltantes > 0 else "Todos los requisitos aplicables han sido cumplidos satisfactoriamente.",
        "tipo_resolucion": resolucion.tipo_resolucion,
        "motivo_resolucion": resolucion.motivo_resolucion,
        "analisis_resolucion": resolucion.descripcion_resolucion
    }
    
    # Preparar datos finales
    datos_analisis = {
        **resumen_analisis,
        "tabs": [tab_solicitud_lista, tab_acta_eleccion_interna, tab_hoja_vida_candidatos, tab_plan_gobierno],
        "numero_expediente": expediente.numero_expediente,
        "nombre_expediente": expediente.nombre_expediente,
        "tipo_expediente": expediente.tipo_expediente.descripcion,
        "materia": expediente.materia.descripcion,
        "id_expediente": id_expediente
    }
    
    # Obtener normativas de la base de datos
    leyes = []
    reglamentos = []
    
    if resolucion and resolucion.normativas:
        normativas = json.loads(resolucion.normativas)
        if isinstance(normativas, list) and len(normativas) >= 2:
            leyes = normativas[0]
            reglamentos = normativas[1]
    # Agregar normativas al contexto
    datos_analisis['normativas'] = [leyes, reglamentos]
    
    # Usar el mismo template que usa procesar_expediente
    return templates.TemplateResponse("views/inscripcion_lista.html", {"request": request, "analisis_realizado": True, **datos_analisis})

@router.post("/generar_resolucion", response_class=HTMLResponse)
async def generar_resolucion(
    request: Request, 
    nombre_expediente: str = Query(...),
    db: Session = Depends(get_db)
):
    """Genera una resolución para un expediente específico"""
    try:
        # Obtener el body JSON
        body = await request.json()
        normativas = body.get('normativas', None)

        # 1. Obtener el expediente
        expediente = await asyncio.to_thread(
            lambda: db.query(Expediente).filter(Expediente.nombre_expediente == nombre_expediente).first()
        )
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # 2. Llamar al servicio de IA para generar la resolución
        resultado = await asyncio.to_thread(generar_resolucion_ia, nombre_expediente)
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])

        # 3. Actualizar la resolución en la base de datos
        resolucion = await asyncio.to_thread(
            lambda: db.query(Resolucion).filter(Resolucion.id_expediente == expediente.id_expediente).first()
        )
        if resolucion:
            resolucion.id_estado = 5  # Estado COMPLETADO
            resolucion.archivo_resolucion = resultado["nombre_archivo"]
            resolucion.modificado_por = "ELECCIA"
            resolucion.fecha_modificacion = func.current_timestamp()
        else:
            # Crear nueva resolución si no existe
            resolucion = Resolucion(
                id_expediente=expediente.id_expediente,
                codigo_resolucion=f"RES-{nombre_expediente}",
                tipo_resolucion="RESOLUCIÓN DE INSCRIPCIÓN",
                id_estado=5,  # Estado COMPLETADO
                archivo_resolucion=resultado["nombre_archivo"],
                creado_por="ELECCIA"
            )
            db.add(resolucion)

        # 4. Actualizar el estado del expediente
        expediente.id_estado = 5  # Estado COMPLETADO
        expediente.modificado_por = "ELECCIA"
        expediente.modificado_en = func.current_timestamp()

        # 5. Guardar cambios
        await asyncio.to_thread(db.commit)

        # 6. Redirigir al listado de procesados
        return RedirectResponse(url="/listado_procesados", status_code=303)

    except Exception as e:
        await asyncio.to_thread(db.rollback)
        raise HTTPException(status_code=500, detail=f"Error al generar la resolución: {str(e)}")

@router.get("/descargar_resolucion/{id_expediente}", response_class=FileResponse)
async def descargar_resolucion(id_expediente: int, db: Session = Depends(get_db)):
    """Descarga la resolución de un expediente específico"""
    try:
        # 1. Obtener el expediente y su resolución
        expediente = await asyncio.to_thread(
            lambda: db.query(Expediente).filter(Expediente.id_expediente == id_expediente).first()
        )
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        resolucion = await asyncio.to_thread(
            lambda: db.query(Resolucion).filter(Resolucion.id_expediente == id_expediente).first()
        )
        if not resolucion or not resolucion.archivo_resolucion:
            raise HTTPException(status_code=404, detail="No se encontró la resolución")

        # 2. Construir la ruta completa del archivo
        ruta_archivo = os.path.join(
            BASE_PATH_DOCUMENTOS,
            expediente.nombre_expediente,
            "resoluciones",
            resolucion.archivo_resolucion
        )

        # 3. Verificar que el archivo existe
        if not os.path.exists(ruta_archivo):
            raise HTTPException(status_code=404, detail="No se encontró el archivo de resolución")

        # 4. Devolver el archivo
        return FileResponse(
            path=ruta_archivo,
            filename=resolucion.archivo_resolucion,
            media_type='application/pdf'
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al descargar la resolución: {str(e)}")

@router.post("/actualizar_estado_requisito", response_class=HTMLResponse)
async def actualizar_requisito(
    request: Request,
    id_expediente: int = Form(...),
    id_estado_requisito: int = Form(...),
    estado: str = Form(...),
    observacion: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Actualiza el estado de un requisito en la base de datos.
    Maneja la concurrencia y reintentos en caso de error.
    """
    try:
        # Obtener el requisito actual con sus relaciones
        requisito = db.query(EstadoRequisitoExpediente).options(
            joinedload(EstadoRequisitoExpediente.configuracion).joinedload(ConfiguracionRequisito.requisito)
        ).filter(
            EstadoRequisitoExpediente.id_estado_requisito == id_estado_requisito
        ).first()
        
        if not requisito:
            raise HTTPException(status_code=404, detail="Requisito no encontrado")
            
        # Obtener el ID del estado
        estado_db = db.query(Estado).filter(Estado.codigo_estado == estado).first()
        if not estado_db:
            raise HTTPException(status_code=400, detail="Estado no válido")
            
        # Actualizar el estado del requisito con manejo de concurrencia
        try:
            actualizar_estado_requisito(
                db=db,
                id_expediente=id_expediente,
                codigo_requisito=requisito.configuracion.requisito.codigo_requisito,
                cumple=estado == 'CUMPLE',
                mensaje=observacion or '',
                usuario='SISTEMA',
                id_candidato=requisito.id_candidato,
                tipo_requisito=requisito.tipo_requisito,
                nueva_sesion=True  # Usar nueva sesión para evitar bloqueos
            )
            
            # Obtener los totales actualizados
            total_requisitos = db.query(EstadoRequisitoExpediente).filter(
                EstadoRequisitoExpediente.id_expediente == id_expediente
            ).count()
            
            requisitos_cumplidos = db.query(EstadoRequisitoExpediente).filter(
                and_(
                    EstadoRequisitoExpediente.id_expediente == id_expediente,
                    EstadoRequisitoExpediente.id_estado_validacion == 7  # CUMPLE
                )
            ).count()
            
            requisitos_faltantes = db.query(EstadoRequisitoExpediente).filter(
                and_(
                    EstadoRequisitoExpediente.id_expediente == id_expediente,
                    EstadoRequisitoExpediente.id_estado_validacion.in_([8, 10])  # NO_CUMPLE, PENDIENTE
                )
            ).count()
            
            porcentaje_cumplimiento = round((requisitos_cumplidos / total_requisitos) * 100) if total_requisitos > 0 else 0
            
            return {
                "success": True,
                "total_requisitos": total_requisitos,
                "requisitos_cumplidos": requisitos_cumplidos,
                "requisitos_faltantes": requisitos_faltantes,
                "porcentaje_cumplimiento": porcentaje_cumplimiento
            }
            
        except Exception as e:
            print(f"Error al actualizar estado de requisito: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except Exception as e:
        print(f"Error en actualizar_estado_requisito: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/guardar_cambios_requisitos")
async def guardar_cambios_requisitos(
    request: Request,
    id_expediente: int = Form(...),
    db: Session = Depends(get_db)
):
    """Guarda todos los cambios de requisitos y actualiza la calificación"""
    try:
        # Obtener el expediente
        expediente = await asyncio.to_thread(
            lambda: db.query(Expediente).filter(Expediente.id_expediente == id_expediente).first()
        )
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        # Obtener los requisitos que fueron editados desde el formulario
        form_data = await request.form()        
        requisitos_editados = []
        
        # Procesar los datos del formulario para obtener los requisitos editados
        for key, value in form_data.items():
            if key.startswith('requisito_'):
                id_estado_requisito = int(key.split('_')[1])
                estado = value
                observacion = form_data.get(f'observacion_{id_estado_requisito}', '')
                
                requisitos_editados.append({
                    'id_estado_requisito': id_estado_requisito,
                    'estado': estado,
                    'observacion': observacion
                })        
        
        # Actualizar solo los requisitos que fueron editados
        for req in requisitos_editados:
            requisito = await asyncio.to_thread(
                lambda: db.query(EstadoRequisitoExpediente).filter(
                    EstadoRequisitoExpediente.id_expediente == id_expediente,
                    EstadoRequisitoExpediente.id_estado_requisito == req['id_estado_requisito']
                ).first()
            )
            
            if requisito:
                # Guardar el estado anterior antes de actualizar
                requisito.validacion_anterior = requisito.validado_por
                # Actualizar el estado según el valor recibido
                if req['estado'] == "CUMPLE":
                    requisito.id_estado_validacion = 7
                elif req['estado'] == "NO_CUMPLE":
                    requisito.id_estado_validacion = 8
                elif req['estado'] == "ALERTA":
                    requisito.id_estado_validacion = 10
                requisito.observaciones = req['observacion']
                requisito.validado_por = "ADMIN"
                requisito.modificado_por = "ADMIN"
                requisito.fecha_modificacion = func.current_timestamp()
        
        # Actualizar el estado del expediente a "EN_PROCESO"
        expediente.id_estado = 4  # EN_PROCESO
        expediente.modificado_por = "ELECCIA"
        expediente.modificado_en = func.current_timestamp()
        
        # Hacer commit de los cambios de requisitos y expediente
        await asyncio.to_thread(db.commit)
        
        # Recalcular contadores de requisitos desde la base de datos
        total_requisitos = await asyncio.to_thread(
            lambda: db.query(EstadoRequisitoExpediente).filter(
                EstadoRequisitoExpediente.id_expediente == id_expediente
            ).count()
        )
        
        requisitos_cumplidos = await asyncio.to_thread(
            lambda: db.query(EstadoRequisitoExpediente).filter(
                EstadoRequisitoExpediente.id_expediente == id_expediente,
                EstadoRequisitoExpediente.id_estado_validacion == 7  # CUMPLE
            ).count()
        )
        
        requisitos_faltantes = total_requisitos - requisitos_cumplidos
        
        
        # Llamar al servicio de calificación para actualizar el front
        calificacion = await asyncio.to_thread(calificacion_resolucion, expediente.nombre_expediente)
        if "error" in calificacion:
            raise HTTPException(status_code=500, detail=calificacion["error"])
            
        # Obtener la última resolución del expediente
        resolucion = await asyncio.to_thread(
            lambda: db.query(Resolucion).filter(
                Resolucion.id_expediente == id_expediente
            ).order_by(Resolucion.fecha_creacion.desc()).first()
        )
        
        if not resolucion:
            # Si no existe resolución, crear una nueva
            resolucion = Resolucion(
                id_expediente=id_expediente,
                codigo_resolucion=f"RES-{expediente.nombre_expediente}",
                id_estado=4,  # EN_PROCESO
                creado_por="ELECCIA"
            )
            db.add(resolucion)
        
        calificacion_md = await asyncio.to_thread(md.markdown, calificacion.get('analisis', ''))
        veredicto = calificacion.get('veredicto', '')
        
        # Actualizar tipo y motivo según el veredicto
        if veredicto == "IMPROCEDENTE":
            resolucion.tipo_resolucion = "Resolución de Improcedencia"
            resolucion.motivo_resolucion = "Incumplimiento de requisitos esenciales de solicitud de inscripción."
        elif veredicto == "INADMISIBLE":
            resolucion.tipo_resolucion = "Resolución de Inadmisibilidad"
            resolucion.motivo_resolucion = "Incumplimiento de requisitos formales que pueden ser subsanados."
        else:  # ADMISIBLE
            resolucion.tipo_resolucion = "Resolución de Admisión"
            resolucion.motivo_resolucion = "Cumple con todos los requisitos esenciales para la inscripción."
            
        resolucion.descripcion_resolucion = calificacion_md
        resolucion.modificado_por = "ELECCIA"
        resolucion.fecha_modificacion = func.current_timestamp()
        
        # Actualizar contadores en la resolución
        resolucion.total_requisitos = total_requisitos
        resolucion.requisitos_cumplidos = requisitos_cumplidos
        resolucion.requisitos_faltantes = requisitos_faltantes
        
        # Hacer commit de los cambios de la resolución
        await asyncio.to_thread(db.commit)
        
        # Redirigir a la página de análisis del expediente
        return RedirectResponse(
            url=f"/ver_analisis_expediente?id_expediente={id_expediente}",
            status_code=303
        )
        
    except Exception as e:
        await asyncio.to_thread(db.rollback)
        raise HTTPException(status_code=500, detail=f"Error al guardar los cambios: {str(e)}")
    finally:
        db.close()

