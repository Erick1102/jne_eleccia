import httpx
import json
from fastapi import HTTPException
import logging
from typing import Tuple, Dict
from app.database.db_scripts import Resumen_PG
from app.database.db_session import SessionLocal

logger = logging.getLogger(__name__)

def validar_firma_digital(file_name: str, n_exp: str) -> Tuple[bool, str]:
    """
    Realiza la validación de firma de lista mediante una API externa.
    Retorna una tupla con (cumple_firma, mensaje_firma)
    """
    try:
        url = "http://192.168.26.118:8000/solicitud_lista/solicitud_lista_validation"
        
        params = {
            "file_name": file_name,
            "n_exp": n_exp
        }
        
        logger.info(f"Intentando validar firma para archivo: {file_name}, expediente: {n_exp}")
        
        # Configurar timeout más largo
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        # Usamos httpx de forma síncrona con timeout configurado
        with httpx.Client(timeout=timeout) as client:
            logger.info(f"Enviando solicitud a: {url}")
            response = client.post(url, params=params)
            logger.info(f"Respuesta recibida: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Error en la API externa: {response.status_code} - {response.text}")
            return None, "ELECCIA no pudo verificar este requisito, validar"
        
        respuesta = response.json()
        
        # Verificar si la respuesta contiene los datos esperados
        if 'resultado' in respuesta:
            resultado = respuesta['resultado']
            datos_personales = resultado.get('datos_personales', '')
            dni = resultado.get('dni', '')
            
            if datos_personales:
                if dni:
                    mensaje = f"Documento firmado digitalmente por el personero legal, {datos_personales}, identificado con DNI {dni}"
                else:
                    mensaje = f"Documento firmado digitalmente por el personero legal, {datos_personales}, la firma digital ha caducado"
                return True, mensaje
            else:
                return False, "No se encontraron datos del firmante"
        else:
            logger.error("La respuesta de la API firma no contiene el campo resultado esperado")
            return None, "ELECCIA no pudo verificar este requisito, validar"
    
    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API firma: {str(e)}")
        return None, "ELECCIA no pudo verificar este requisito, validar"
    
    except httpx.RequestError as e:
        logger.error(f"Error de conexión con la API firma: {str(e)}")
        return None, "ELECCIA no pudo verificar este requisito, validar"
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return None, "ELECCIA no pudo verificar este requisito, validar"

def extraer_datos_acta(num_expediente: str, ubigeo: str) -> Dict:
    """
    Extrae los datos del acta de elección interna del expediente.
    
    Args:
        num_expediente: Número del expediente a procesar
        ubigeo: Ubigeo donde se postula
        
    Returns:
        Dict: Diccionario con los datos extraídos del acta
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8000/eleccion_interna/eleccion_interna_validation"
        params = {
            "file_name": "ACTA_DE_ELECCION_INTERNA.pdf",
            "n_exp": num_expediente,
            "ubigeo": ubigeo
        }
        
        # Configurar timeout
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        # Realizar la solicitud HTTP
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, params=params)
            
        if response.status_code != 200:
            logger.error(f"Error en la API acta: {response.status_code} - {response.text}")
            return {"error": "Error al comunicarse con el servicio de validación"}
            
        respuesta = response.json()
        
        if 'resultado' in respuesta:
            return respuesta['resultado']
        else:
            logger.error("La respuesta no contiene el campo resultado esperado")
            return {"error": "Formato de respuesta inválido"}
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API acta: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión acta: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado acta: {str(e)}")
        return {"error": "Error interno del servidor"}

def generar_resolucion_ia(num_expediente: str) -> Dict:
    """
    Genera una resolución para un expediente específico
    
    Args:
        num_expediente: ID del expediente a procesar
    
    Returns:
        Dict: Diccionario con la resolución generada
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8006/generacion_resolucion/resolucion"
        params = {
            "n_exp": num_expediente,
            "tipo_res": 1
        }
        
        # Datos para el body de la petición
        datos = {
            "distrito": "San Miguel",
            "provincia": "Lima", 
            "departamento": "Lima",
            "personero": "Carlos Fernández",
            "organizacion": "Partido Unido del Pueblo",
            "evento": "Elecciones Regionales 2025",
            "presidente": "Ana Rodríguez",
            "segundo_miembro": "Luis Torres",
            "tercer_miembro": "María Huamán",
            "secretario": "Jorge Quispe",
            "veredicto": "Válido sin observaciones"
        }
        
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, params=params, json=datos)
            
        if response.status_code == 303:
            redirect_url = response.headers.get('Location')
            if redirect_url:
                response = client.get(redirect_url)
            
        if response.status_code != 200:
            logger.error(f"Error en la API resolución: {response.status_code} - {response.text}")
            return {"error": "Error al comunicarse con el servicio de generación de resolución"}
            
        respuesta = response.json()
        
        if 'message' in respuesta and 'results' in respuesta:
            return {
                "mensaje": respuesta['message'],
                "nombre_archivo": respuesta['results']
            }
        else:
            logger.error("La respuesta no contiene los campos esperados")
            return {"error": "Formato de respuesta inválido"}

    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API resolución: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {"error": "Error interno del servidor"}

def calificacion_resolucion(num_expediente: str) -> Dict:
    """
    Obtiene la calificación de la resolución para un expediente específico
    
    Args:
        num_expediente: Número del expediente a procesar
    
    Returns:
        Dict: Diccionario con la calificación de la resolución
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8006/generacion_resolucion/calificacion_resolucion"
        params = {
            "n_exp": num_expediente
        }
        
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, params=params)
            
        if response.status_code != 200:
            logger.error(f"Error en la API califica resolucion: {response.status_code} - {response.text}")
            return {"error": "Error al comunicarse con el servicio de calificación de resolución"}
            
        respuesta = response.json()
        
        if 'message' in respuesta and 'analisis' in respuesta and 'veredicto' in respuesta:
            return {
                "mensaje": respuesta['message'],
                "analisis": respuesta['analisis'],
                "veredicto": respuesta['veredicto']
            }
        else:
            logger.error("La respuesta de la API califica resolucion no contiene los campos esperados")
            return {"error": "Formato de respuesta inválido"}

    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API califica resolución: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {"error": "Error interno del servidor"}

def plan_gobierno(num_expediente: str) -> Dict:
    """
    Obtiene la calificación del plan de gobierno para un expediente específico
    
    Args:
        num_expediente: Número del expediente a procesar
    
    Returns:
        Dict: Diccionario con la calificación del plan de gobierno
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8000/plan_de_gobierno/calificacion_plan_de_gobierno"
        params = {
            "file_name": "PLAN_DE_GOBIERNO.pdf",
            "n_exp": num_expediente
        }
        
        # Obtener datos del plan de gobierno desde la base de datos
        db = SessionLocal()
        try:
            result = db.execute(Resumen_PG, {"TXCODEXPEDIENTEEXT": num_expediente}).fetchall()
            
            if not result:
                return {"error": "No se encontraron datos del plan de gobierno"}
                
            # Organizar los datos para el body
            organizacion_politica = result[0][0]
            ideario = result[0][1]
            mision = result[0][2]
            
            # Inicializar el diccionario de propuestas
            propuestas = {
                "dimension_social": [],
                "dimension_economica": [],
                "dimension_ambiental": [],
                "dimension_institucional": []
            }
            
            # Procesar cada registro
            for row in result:
                dimension = row[7]  # IDPGDIMENSION
                problema = row[3]
                objetivo = row[4]
                meta = row[5]
                indicador = row[6]
                
                # Determinar la dimensión correspondiente
                if dimension == 1:
                    propuestas["dimension_social"].append({
                        "problema": problema,
                        "objetivo": objetivo,
                        "meta": meta,
                        "indicador": indicador
                    })
                elif dimension == 2:
                    propuestas["dimension_economica"].append({
                        "problema": problema,
                        "objetivo": objetivo,
                        "meta": meta,
                        "indicador": indicador
                    })
                elif dimension == 3:
                    propuestas["dimension_ambiental"].append({
                        "problema": problema,
                        "objetivo": objetivo,
                        "meta": meta,
                        "indicador": indicador
                    })
                elif dimension == 4:
                    propuestas["dimension_institucional"].append({
                        "problema": problema,
                        "objetivo": objetivo,
                        "meta": meta,
                        "indicador": indicador
                    })
            
            # Preparar el body de la petición
            body = {
                "organizacion_politica": organizacion_politica,
                "ideario": ideario,
                "mision": mision,
                "propuestas": propuestas
            }
            
            timeout = httpx.Timeout(90.0, connect=10.0)
            
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, params=params, json=body)
                
            if response.status_code != 200:
                logger.error(f"Error en la API plan de gobierno: {response.status_code} - {response.text}")
                return {"error": "Error al comunicarse con el servicio de calificación del plan de gobierno"}
                
            respuesta = response.json()
            
            if 'message' in respuesta and 'resultado' in respuesta:
                return {
                    "message": respuesta['message'],
                    "resultado": respuesta['resultado']
                }
            else:
                logger.error("La respuesta de la API plan de gobierno no contiene los campos esperados")
                return {"error": "Formato de respuesta inválido"}
                
        finally:
            db.close()

    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API plan de gobierno: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {"error": "Error interno del servidor"} 
    
def verificar_ddjj(file_name: str, num_expediente: str, dni: str, id_anexo: int) -> Dict:
    """
    Verifica una Declaración Jurada específica mediante una API externa.
    
    Args:
        file_name: Nombre del archivo de la DDJJ
        num_expediente: Número del expediente a procesar
        dni: DNI del candidato
        id_anexo: ID del tipo de anexo/DDJJ
    
    Returns:
        Dict: Diccionario con la información extraída de la DDJJ
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8000/anexos/anexo"
        params = {
            "file_name": file_name,
            "n_exp": num_expediente,
            "dni": dni,
            "id_anexo": id_anexo
        }
        
        logger.info(f"Intentando verificar DDJJ: {file_name}, expediente: {num_expediente}, DNI: {dni}")
        
        # Configurar timeout
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        # Realizar la solicitud HTTP
        with httpx.Client(timeout=timeout) as client:
            logger.info(f"Enviando solicitud a: {url}")
            response = client.post(url, params=params)
            logger.info(f"Respuesta recibida: {response.status_code}")
            
        if response.status_code != 200:
            logger.error(f"Error en la API DJJ: {response.status_code} - {response.text}")
            return {"error": f"Error al comunicarse con el servicio de verificación de DDJJ: {response.status_code}"}
            
        respuesta = response.json()
        
        # Verificar si la respuesta contiene los datos esperados
        if 'resultado' in respuesta:
            return respuesta['resultado']
        else:
            logger.error("La respuesta de la API DJJ no contiene el campo resultado esperado")
            return {"error": "Formato de respuesta inválido"}
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API de DDJJ: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {"error": "Error interno del servidor"}
    
def validar_comprobante_pago(file_name: str, num_expediente: str, dni: str) -> Dict:
    """
    Valida un comprobante de pago mediante una API externa.
    
    Args:
        file_name: Nombre del archivo del comprobante
        num_expediente: Número del expediente a procesar
        dni: DNI del candidato o personero
    
    Returns:
        Dict: Diccionario con la información extraída del comprobante de pago
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8000/voucher/voucher_validation"
        params = {
            "file_name": file_name,
            "n_exp": num_expediente,
            "dni": dni
        }
        
        logger.info(f"Intentando validar comprobante de pago: {file_name}, expediente: {num_expediente}, DNI: {dni}")
        
        # Configurar timeout
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        # Realizar la solicitud HTTP
        with httpx.Client(timeout=timeout) as client:
            logger.info(f"Enviando solicitud a: {url}")
            response = client.post(url, params=params)
            logger.info(f"Respuesta recibida: {response.status_code}")
            
        if response.status_code != 200:
            logger.error(f"Error en la API de comprobante: {response.status_code} - {response.text}")
            return {"error": f"Error al comunicarse con el servicio de validación de comprobante: {response.status_code}"}
            
        respuesta = response.json()
        
        # Verificar si la respuesta contiene los datos esperados
        if 'message' in respuesta and 'resultado' in respuesta:
            return respuesta
        else:
            logger.error("La respuesta de la API de comprobante no contiene los campos esperados")
            return {"error": "Formato de respuesta inválido"}
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API de comprobante: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {"error": "Error interno del servidor"}

def obtener_normativas(num_expediente: str) -> Dict:
    """
    Obtiene las normativas relacionadas a un expediente específico mediante una API externa.
    
    Args:
        num_expediente: Número del expediente a procesar
    
    Returns:
        Dict: Diccionario con las normativas relacionadas al expediente
    """
    try:
        # Configurar la URL y parámetros
        url = "http://192.168.26.118:8000/generacion_resolucion/normativas"
        params = {
            "n_exp": num_expediente
        }
        
        logger.info(f"Intentando obtener normativas para expediente: {num_expediente}")
        
        # Configurar timeout
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        # Realizar la solicitud HTTP
        with httpx.Client(timeout=timeout) as client:
            logger.info(f"Enviando solicitud a: {url}")
            response = client.get(url, params=params)
            logger.info(f"Respuesta recibida: {response.status_code}")
            
        if response.status_code != 200:
            logger.error(f"Error en la API de normativas: {response.status_code} - {response.text}")
            return {"error": f"Error al comunicarse con el servicio de normativas: {response.status_code}"}
            
        respuesta = response.json()
        
        # Verificar si la respuesta contiene los datos esperados
        if 'results' in respuesta:
            return respuesta['results']
        else:
            logger.error("La respuesta de la API de normativas no contiene el campo results")
            return {"error": "Formato de respuesta inválido"}
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout al conectar con la API de normativas: {str(e)}")
        return {"error": "El servicio no respondió a tiempo"}
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return {"error": "No se pudo conectar con el servicio"}
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {"error": "Error interno del servidor"}
    