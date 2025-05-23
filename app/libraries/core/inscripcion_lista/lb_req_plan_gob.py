"""
Validación de los requisitos del plan de gobierno.
"""

from app.libraries.lb_utils import obtener_id_expediente_eleccia
from app.database.db_session import get_db
from app.services.sr_ia_services import plan_gobierno
from app.database.models.db_models_eleccia import EstadoRequisitoExpediente

usuario = 'ADMIN'

def validar_concordancia_plan_gob(db, id_expediente: int, num_expediente: str, url_plangob: str = None) -> tuple[bool, str]:
    """
    Valida la concordancia entre el plan de gobierno y su resumen.
    """
    try:
        # Llamar al servicio de IA para validar el plan de gobierno
        resultado = plan_gobierno(num_expediente)
        
        if "error" in resultado:
            return False, resultado["error"]
            
        # Obtener los porcentajes de concordancia
        porcentajes = resultado.get("resultado", {})
        
        # Definir umbrales mínimos para considerar que cumple
        umbral_minimo = 70.0  # 70% de concordancia mínimo
        
        # Verificar si todos los porcentajes superan el umbral mínimo
        cumple = all(valor >= umbral_minimo for valor in porcentajes.values())
        
        # Construir mensaje detallado
        mensaje = "Análisis de concordancia del plan de gobierno:<br>"
        for seccion, valor in porcentajes.items():
            estado = "Cumple" if valor >= umbral_minimo else "No cumple"
            mensaje += f"- {seccion}: ({estado})<br>"
            
        if cumple:
            mensaje += "<br>El plan de gobierno cumple con los requisitos de concordancia."
        else:
            mensaje += f"<br>El plan de gobierno no cumple con los requisitos de concordancia."
        
        return cumple, mensaje
        
    except Exception as e:
        return False, f"Error al validar concordancia del plan de gobierno: {str(e)}"

def validar_firma_plan_gob(db, id_expediente: int) -> tuple[bool, str]:
    """
    Valida la firma del plan de gobierno.
    Por ahora retorna que cumple.
    """
    cumple = True
    mensaje = "La firma del plan de gobierno cumple con los requisitos."
    
    return cumple, mensaje

def validar_requisitos_plan_gob(num_expediente: str, urls_documentos: dict = None) -> dict:
    """
    Valida todos los requisitos del plan de gobierno.
    """
    from concurrent.futures import ThreadPoolExecutor
    import concurrent.futures

    resultados = {}
    db = next(get_db())

    try:
        # Obtener ID de expediente
        id_expediente = obtener_id_expediente_eleccia(db, num_expediente)
        if not id_expediente:
            return {"error": "No se encontró el expediente"}    
        
        url_plangob = None
        if urls_documentos and 'PLAN_DE_GOBIERNO' in urls_documentos:
            url_plangob = urls_documentos['PLAN_DE_GOBIERNO']['url']   

        # Crear funciones auxiliares para cada validación
        def ejecutar_validacion_concordancia():
            cumple, mensaje = validar_concordancia_plan_gob(db, id_expediente, num_expediente, None)
            return 'PLAN_GOBIERNO', {
                'cumple': cumple,
                'mensaje': mensaje,
                'url_documento': url_plangob
            }

        def ejecutar_validacion_firma():
            cumple, mensaje = validar_firma_plan_gob(db, id_expediente)
            return 'FIRMA_PLAN_GOB', {
                'cumple': cumple,
                'mensaje': mensaje,
                'url_documento': url_plangob
            }

        # Ejecutar todas las validaciones en paralelo
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_validacion = {
                executor.submit(ejecutar_validacion_concordancia): 'PLAN_GOBIERNO'
                #executor.submit(ejecutar_validacion_firma): 'FIRMA_PLAN_GOB'
            }

            # Recopilar resultados cuando estén disponibles
            for future in concurrent.futures.as_completed(future_to_validacion):
                try:
                    codigo, resultado = future.result()
                    resultados[codigo] = resultado
                except Exception as e:
                    codigo = future_to_validacion[future]
                    resultados[codigo] = {
                        'cumple': False,
                        'mensaje': f"Error en la validación: {str(e)}",
                        'url_documento': url_plangob
                    }
        
        return resultados
    
    except Exception as e:
        return {"error": f"Error al validar requisitos del plan de gobierno: {str(e)}"}
    finally:
        db.close()

