"""
Validación de los requisitos de la acta de elección interna.
"""
from app.database.db_session import get_db
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

from app.libraries.lb_utils import obtener_id_expediente_eleccia, actualizar_estado_requisito, verificar_estado_requisito
from app.services.sr_ia_services import extraer_datos_acta
from app.database.models.db_models_eleccia import EstadoRequisitoExpediente, ConfiguracionRequisito, Requisito


usuario = 'ELECCIA'


def validar_acta_plazo(db, id_expediente: int, fecha_acta: str, modalidad: str, url_acta: str = None) -> tuple[bool, str]:
    """
    Valida que el acta de elección se haya realizado dentro del plazo establecido según la modalidad.
    La fecha del acta debe ser anterior o igual a la fecha límite.
    
    Args:
        db: Sesión de base de datos
        id_expediente: ID del expediente
        fecha_acta: Fecha del acta en formato DD/MM/YYYY
        modalidad: Modalidad de elección ('votación' o 'afiliados')
        
    Returns:
        Tuple con (cumple, mensaje)
    """
    try:
        # Verificar si la fecha del acta es None o vacía
        if not fecha_acta:
            mensaje = "No se encontró la fecha del acta de elección interna"
            cumple = False
        else:
            # Convertir fecha del acta a datetime
            fecha_acta_dt = datetime.strptime(fecha_acta, "%d/%m/%Y").date()
            
            # Obtener fechas límite según modalidad
            if modalidad.lower() == 'delegados':
                fecha_limite = datetime(2022, 5, 22).date()  # Fecha límite para delegados
            else:  # afiliados
                fecha_limite = datetime(2022, 5, 15).date()  # Fecha límite para afiliados
            
            # Verificar que la fecha del acta no exceda la fecha límite
            cumple = fecha_acta_dt <= fecha_limite
            
            # Construir mensaje descriptivo
            if cumple:
                mensaje = f"Elección interna realizada el {fecha_acta} dentro del plazo de {modalidad}, según calendario electoral {fecha_limite.strftime('%d/%m/%Y')}."
            else:
                mensaje = f"Elección interna realizada el {fecha_acta} fuera de la fecha límite del {fecha_limite.strftime('%d/%m/%Y')} para {modalidad}, según calendario electoral."
        
        return cumple, mensaje
        
    except Exception as e:
        mensaje = f"Error al validar plazo del acta: {str(e)}"
        return False, mensaje

def validar_lugar_electoral(db, id_expediente: int, ubigeo_acta: str, ubigeo_postula: str, url_acta: str = None) -> tuple[bool, str]:
    """
    Valida que el lugar electoral indicado en el acta coincida con el ubigeo de postulación.
    
    Args:
        db: Sesión de base de datos
        id_expediente: ID del expediente
        ubigeo_acta: Ubigeo indicado en el acta
        ubigeo_postula: Ubigeo donde se postula
        
    Returns:
        Tuple con (cumple, mensaje)
    """
    try:
        cumple = ubigeo_acta.upper() == ubigeo_postula
        mensaje = f"Los ubigeos coinciden, ubigeo en acta: {ubigeo_acta}, ubigeo de postulación: {ubigeo_postula}"
        if not cumple:
            mensaje += f"Los ubigeos no coinciden, ubigeo en acta: {ubigeo_acta}, ubigeo de postulación: {ubigeo_postula}"
        
        return cumple, mensaje
        
    except Exception as e:
        mensaje = f"Error al validar lugar electoral: {str(e)}"
        return False, mensaje

def validar_acta_lista_candidatos(db, id_expediente: int, candidatos_acta: list[dict], candidatos_solicitud: dict, url_acta: str = None) -> tuple[bool, str]:
    """
    Valida que la lista de candidatos en el acta coincida con la lista de solicitud.
    Se enfoca solo en los datos esenciales: DNI, nombre completo y cargo.
    
    Args:
        db: Sesión de base de datos
        id_expediente: ID del expediente
        candidatos_acta: Lista de candidatos del acta
        candidatos_solicitud: Diccionario de candidatos de la solicitud
        
    Returns:
        Tuple con (cumple, mensaje)
    """
    try:
        def verificar_cargo_coincide(cargo_acta: str, cargo_solicitud: str) -> bool:
            """
            Verifica si el cargo del acta coincide con el cargo de la solicitud.
            El cargo del acta debe contener la palabra clave del cargo de la solicitud.
            """
            cargo_acta = cargo_acta.strip().upper()
            cargo_solicitud = cargo_solicitud.strip().upper()
            
            # Extraer la palabra clave del cargo de la solicitud (ALCALDE o REGIDOR)
            palabra_clave = cargo_solicitud.split()[0]  # Obtiene "ALCALDE" o "REGIDOR"
            
            return palabra_clave in cargo_acta

        # Convertir diccionario de candidatos a lista ordenada
        candidatos_sol_lista = []
        for dni, candidatos in candidatos_solicitud.items():
            for candidato in candidatos:
                # Unir nombres y apellidos para una comparación simplificada
                nombre_completo = f"{candidato['tx_nombres']} {candidato['tx_apellidos']}".strip().upper()
                candidatos_sol_lista.append({
                    'dni': candidato['tx_dni'],
                    'nombre_completo': nombre_completo,
                    'cargo': candidato['tx_cargo_eleccion'].strip().upper(),
                    'tx_nuposicion': candidato['tx_nuposicion']
                })
        
        # Ordenar por posición
        candidatos_sol_lista.sort(key=lambda x: int(x.get('tx_nuposicion', 0)))
        
        # Preparar lista de acta para comparación
        candidatos_acta_procesados = []
        for candidato in candidatos_acta:
            # Extraer el nombre completo directamente del acta
            nombre_completo = candidato.get('datos_personales', '').strip().upper()
            nombre_completo = re.sub(r'\.+$', '', nombre_completo).strip()
            
            candidatos_acta_procesados.append({
                'dni': candidato.get('dni', '').strip(),
                'nombre_completo': nombre_completo,
                'cargo': candidato.get('cargo', '').strip().upper()
            })
        
        # Verificar que ambas listas tengan la misma cantidad de candidatos principales
        candidatos_acta_principales = [c for c in candidatos_acta_procesados if 'ACCESITARIO' not in c['cargo'].upper().strip()]
        candidatos_sol_principales = [c for c in candidatos_sol_lista if 'ACCESITARIO' not in c['cargo'].upper().strip()]
        
        if len(candidatos_acta_principales) != len(candidatos_sol_principales):
            mensaje = f"La cantidad de candidatos principales no coincide. Candidatos en Acta: {len(candidatos_acta_principales)}, candidatos en Solicitud: {len(candidatos_sol_principales)}"
            cumple = False
        else:
            # Verificar que cada candidato coincida en orden y datos
            cumple = True
            mensaje = "La lista de candidatos principales coincide con el acta"
            
            for i, (cand_acta, cand_sol) in enumerate(zip(candidatos_acta_principales, candidatos_sol_principales)):
                # Comparar DNI y verificar si el cargo coincide
                if cand_acta['dni'] != cand_sol['dni'] or not verificar_cargo_coincide(cand_acta['cargo'], cand_sol['cargo']):
                    cumple = False
                    mensaje = f"Los candidatos en la posición {i+1} no coinciden:<br>" \
                            f"Acta: {cand_acta['nombre_completo']} ({cand_acta['dni']}) - {cand_acta['cargo']}<br>" \
                            f"Solicitud: {cand_sol['nombre_completo']} ({cand_sol['dni']}) - {cand_sol['cargo']}"
                    break
        
        return cumple, mensaje
        
    except Exception as e:
        mensaje = f"Error al validar lista de candidatos: {str(e)}"
        return False, mensaje

def validar_requisitos_acta_interna(num_expediente: str, info_candidatos: dict, ubigeo_postula: str, urls_documentos: dict = None) -> dict:
    """
    Valida todos los requisitos del acta interna.
    
    Args:
        num_expediente: Número de expediente
        info_candidatos: Diccionario con información de candidatos
        ubigeo_postula: Ubigeo donde se postula
        
    Returns:
        Diccionario con los resultados de cada validación
    """
    from concurrent.futures import ThreadPoolExecutor
    import concurrent.futures

    resultados = {}
    db = next(get_db())
    # Obtener ID de expediente de elección
    id_expediente_eleccia = obtener_id_expediente_eleccia(db, num_expediente)
    if not id_expediente_eleccia:
        return {"error": "No se encontró el expediente"}
    
    # Obtener URL del acta
    url_acta = None
    if urls_documentos and 'ACTA_DE_ELECCION_INTERNA' in urls_documentos:
        url_acta = urls_documentos['ACTA_DE_ELECCION_INTERNA']['url']

    # Extraer datos del acta usando el servicio de IA
    datos_acta = extraer_datos_acta(num_expediente, ubigeo_postula)
    
    # Si hay error en el servicio, marcar todos los requisitos como ALERTA
    if isinstance(datos_acta, dict) and 'error' in datos_acta:
        mensaje = "ELECCIA no pudo verificar este requisito, validar"
        # Marcar todos los requisitos como ALERTA
        for codigo_requisito in ['ACTA_PLAZO', 'UBIGEO_ELECTORAL', 'ACTA_LISTA_CANDIDATOS']:
            resultados[codigo_requisito] = {
                'cumple': None,
                'mensaje': mensaje,
                'url_documento': url_acta
            }
        return resultados

    # Crear funciones auxiliares para cada validación
    def ejecutar_validacion_plazo():
        cumple, mensaje = validar_acta_plazo(db, id_expediente_eleccia, datos_acta.get('fecha_eleccion', ''), datos_acta.get('modalidad', ''), None)
        return 'ACTA_PLAZO', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_acta
        }

    def ejecutar_validacion_lugar():
        cumple, mensaje = validar_lugar_electoral(db, id_expediente_eleccia, datos_acta.get('lugar_electoral', ''), ubigeo_postula, None)
        return 'UBIGEO_ELECTORAL', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_acta
        }

    def ejecutar_validacion_lista():
        cumple, mensaje = validar_acta_lista_candidatos(db, id_expediente_eleccia, datos_acta.get('lista_presentada', []), info_candidatos.get('CANDIDATOS', {}), None)
        return 'ACTA_LISTA_CANDIDATOS', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_acta
        }

    # Ejecutar todas las validaciones en paralelo
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_validacion = {
            executor.submit(ejecutar_validacion_plazo): 'ACTA_PLAZO',
            executor.submit(ejecutar_validacion_lugar): 'UBIGEO_ELECTORAL',
            executor.submit(ejecutar_validacion_lista): 'ACTA_LISTA_CANDIDATOS'
        }

        # Recopilar resultados cuando estén disponibles
        for future in concurrent.futures.as_completed(future_to_validacion):
            try:
                codigo, resultado = future.result()
                resultados[codigo] = resultado
            except Exception as e:
                codigo = future_to_validacion[future]
                resultados[codigo] = {
                    'cumple': None,
                    'mensaje': "ELECCIA no pudo verificar este requisito, validar",
                    'url_documento': url_acta
                }
    
    return resultados


