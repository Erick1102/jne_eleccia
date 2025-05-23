"""
Validación de los requisitos de hoja de vida de los candidatos.
"""

from app.libraries.lb_utils import obtener_id_expediente_eleccia
from app.database.db_session import get_db
from app.database.models.db_models_eleccia import Candidato, EstadoRequisitoExpediente, ConfiguracionRequisito, Requisito
from app.config.cf_constantes import (
    DDJJ_CONSENTIMIENTO,
    DDJJ_DEUDA_REPARACION,
    DDJJ_LICENCIA,
    DDJJ_RENUNCIA,
    DDJJ_EXTRANJERO,
    DDJJ_DOMICILIO_MULTIPLE,
    COMPROBANTE_PAGO,
    DJJ_PLAZO,
    DJJ_HV,
    OTROS,
    MAPEO_REQUISITOS
)
from app.services.sr_ia_services import verificar_ddjj, validar_comprobante_pago
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Tuple, Any
import threading

# Configuración de concurrencia
MAX_WORKERS = 20  # Número máximo de workers para el pool
CACHE_SIZE = 1000  # Tamaño del caché para servicios externos

# Caché para servicios externos
ddjj_cache = {}
comprobante_cache = {}
cache_lock = threading.Lock()

def get_cached_ddjj(file_name: str, num_expediente: str, dni: str, id_anexo: int) -> dict:
    """
    Obtiene el resultado de verificar_ddjj desde el caché o lo ejecuta si no está en caché.
    """
    cache_key = f"{file_name}_{num_expediente}_{dni}_{id_anexo}"
    
    with cache_lock:
        if cache_key in ddjj_cache:
            return ddjj_cache[cache_key]
        
        resultado = verificar_ddjj(file_name, num_expediente, dni, id_anexo)
        ddjj_cache[cache_key] = resultado
        return resultado

def get_cached_comprobante(file_name: str, num_expediente: str, dni: str) -> dict:
    """
    Obtiene el resultado de validar_comprobante_pago desde el caché o lo ejecuta si no está en caché.
    """
    cache_key = f"{file_name}_{num_expediente}_{dni}"
    
    with cache_lock:
        if cache_key in comprobante_cache:
            return comprobante_cache[cache_key]
        
        resultado = validar_comprobante_pago(file_name, num_expediente, dni)
        comprobante_cache[cache_key] = resultado
        return resultado

def procesar_documentos_en_paralelo(documentos: List[dict], num_expediente: str, dni: str) -> Dict[str, dict]:
    """
    Procesa múltiples documentos en paralelo usando un pool de workers.
    """
    resultados = {}
    
    def procesar_documento(doc: dict) -> Tuple[str, dict]:
        nombre = doc['nombre']
        if nombre == DDJJ_CONSENTIMIENTO:
            return nombre, get_cached_ddjj("DDJJ_DE_CONSENTIMIENTO_DE_PARTICIPACIÓN.pdf", num_expediente, dni, 1)
        elif nombre == DDJJ_DEUDA_REPARACION:
            return nombre, get_cached_ddjj("DDJJ_DE_NO_TENER_DEUDA_DE_REPARACIÓN_CIVIL.pdf", num_expediente, dni, 2)
        elif nombre == COMPROBANTE_PAGO:
            return nombre, get_cached_comprobante("COMPROBANTE_DE_PAGO.pdf", num_expediente, dni)
        return nombre, None
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_doc = {executor.submit(procesar_documento, doc): doc for doc in documentos}
        
        for future in as_completed(future_to_doc):
            nombre, resultado = future.result()
            if resultado:
                resultados[nombre] = resultado
    
    return resultados

usuario = 'ADMIN'

def validar_documento_individual(db, id_expediente: int, id_candidato: int, documentos_candidato: list, 
                                codigo_documento: str, info_candidato: dict = None, 
                                num_expediente: str = None, usar_nueva_sesion: bool = True) -> tuple[bool, str, str]:
    """
    Valida si un documento específico está presente en la lista de documentos y verifica su contenido si es una DDJJ.
    Retorna (cumple, mensaje, ruta_archivo)
    """
    from app.database.db_session import get_db
    
    # Inicializar valores por defecto
    cumple = False
    mensaje = f"No se encontró el documento {codigo_documento}"
    url_documento = ""
    fecha_firma = None
    
    # Verificar si el documento existe en la lista
    for doc in documentos_candidato:
        if doc['nombre'] == codigo_documento:
            url_documento = doc.get('url', '')
            fecha_firma = doc.get('fecha_firma')
            
            # Inicializar con verificación básica
            cumple = True
            mensaje = f"Documento {codigo_documento} validado para el candidato."
            
            # Verificación adicional para DDJJ específicas
            if num_expediente and info_candidato:
                dni = info_candidato.get('tx_dni')
                
                if dni:
                    # Procesar documentos en paralelo
                    resultados_docs = procesar_documentos_en_paralelo(documentos_candidato, num_expediente, dni)
                    
                    # Verificar DDJJ de consentimiento
                    if codigo_documento == DDJJ_CONSENTIMIENTO:
                        resultado_ddjj = resultados_docs.get(DDJJ_CONSENTIMIENTO, {})
                        
                        if "error" in resultado_ddjj:
                            cumple = None  # Estado ALERTA
                            mensaje = "ELECCIA no pudo verificar este requisito, validar"
                        else:
                            # Verificar que los datos del candidato coincidan con la DDJJ
                            nombre_ddjj = resultado_ddjj.get('datos_personales', '').upper()
                            nombre_candidato = f"{info_candidato.get('tx_nombres', '')} {info_candidato.get('tx_apellidos', '')}".upper()
                            
                            # Verificación más flexible de nombres
                            if nombre_ddjj and nombre_candidato:
                                if nombre_ddjj in nombre_candidato or nombre_candidato in nombre_ddjj or \
                                any(parte in nombre_candidato for parte in nombre_ddjj.split()):
                                    firma = resultado_ddjj.get('firma', False)
                                    huella = resultado_ddjj.get('huella', False)
                                    
                                    if firma and huella:
                                        cumple = True
                                        mensaje = f"Declaración Jurada de consentimiento correctamente validado con firma y huella del candidato {nombre_candidato}"
                                        if fecha_firma:
                                            try:
                                                fecha_firma_dt = datetime.strptime(str(fecha_firma), '%Y-%m-%d %H:%M:%S.%f')
                                                fecha_formateada = fecha_firma_dt.strftime('%d/%m/%Y')
                                                mensaje += f". Fecha de firma: {fecha_formateada}"
                                            except ValueError:
                                                pass
                                    else:
                                        cumple = False
                                        mensaje = "Declaración Jurada de consentimiento incompleta: "
                                        if not firma:
                                            mensaje += "falta firma, "
                                        if not huella:
                                            mensaje += "falta huella, "
                                        mensaje = mensaje.rstrip(", ")
                                else:
                                    cumple = False
                                    mensaje = f"Los datos del candidato en la Declaración Jurada ({nombre_ddjj}) no coinciden con los registrados ({nombre_candidato})"
                            else:
                                cumple = False
                                mensaje = "No se pueden verificar los nombres en la Declaración Jurada (datos faltantes)"
                    
                    # Verificar DDJJ de no tener deuda de reparación civil
                    elif codigo_documento == DDJJ_DEUDA_REPARACION:
                        resultado_ddjj = resultados_docs.get(DDJJ_DEUDA_REPARACION, {})
                        
                        if "error" in resultado_ddjj:
                            cumple = None  # Estado ALERTA
                            mensaje = "ELECCIA no pudo verificar este requisito, validar"
                        else:
                            # Verificar que los datos del candidato coincidan con la DDJJ
                            nombre_ddjj = resultado_ddjj.get('datos_personales', '').upper()
                            nombre_candidato = f"{info_candidato.get('tx_nombres', '')} {info_candidato.get('tx_apellidos', '')}".upper()
                            
                            # Verificación más flexible de nombres
                            if nombre_ddjj and nombre_candidato:
                                if nombre_ddjj in nombre_candidato or nombre_candidato in nombre_ddjj or \
                                any(parte in nombre_candidato for parte in nombre_ddjj.split()):
                                    firma = resultado_ddjj.get('firma', False)
                                    huella = resultado_ddjj.get('huella', False)
                                    
                                    if firma and huella:
                                        cumple = True
                                        mensaje = f"Declaración Jurada de no deuda correctamente validado con firma y huella del candidato {nombre_candidato}"
                                        if fecha_firma:
                                            try:
                                                fecha_firma_dt = datetime.strptime(str(fecha_firma), '%Y-%m-%d %H:%M:%S.%f')
                                                fecha_formateada = fecha_firma_dt.strftime('%d/%m/%Y')
                                                mensaje += f". Fecha de firma: {fecha_formateada}"
                                            except ValueError:
                                                pass
                                    else:
                                        cumple = False
                                        mensaje = "Declaración Jurada de no deuda incompleta: "
                                        if not firma:
                                            mensaje += "falta firma, "
                                        if not huella:
                                            mensaje += "falta huella, "
                                        mensaje = mensaje.rstrip(", ")
                                else:
                                    cumple = False
                                    mensaje = f"Los datos del candidato en la Declaración Jurada de no deuda ({nombre_ddjj}) no coinciden con el candidato ({nombre_candidato})"
                            else:
                                cumple = False
                                mensaje = "No se pueden verificar los nombres en la Declaración Jurada (datos faltantes)"
                    
                    # Verificar comprobante de pago
                    elif codigo_documento == COMPROBANTE_PAGO:
                        resultado_voucher = resultados_docs.get(COMPROBANTE_PAGO, {})
                        
                        if resultado_voucher is None or "error" in resultado_voucher:
                            cumple = None  # Estado ALERTA
                            mensaje = "ELECCIA no pudo verificar este requisito, validar"
                        else:
                            # Verificar que el DNI coincida
                            datos_voucher = resultado_voucher.get('resultado', {}).get('data', {})
                            if not datos_voucher:
                                cumple = False
                                mensaje = "No se pudo extraer la información del comprobante de pago"
                            else:
                                dni_voucher = datos_voucher.get('dni', '')
                                
                                # Verificar si el DNI del voucher tiene 8 dígitos
                                if len(dni_voucher) == 8:
                                    if dni_voucher != dni:
                                        cumple = False
                                        mensaje = f"El DNI en el comprobante ({dni_voucher}) no coincide con el DNI del candidato ({dni})"
                                    else:
                                        # Verificar que el concepto sea 01155
                                        concepto = datos_voucher.get('concepto', '')
                                        if concepto != '01155':
                                            cumple = False
                                            mensaje = f"El concepto en el comprobante ({concepto}) no es válido. Se esperaba 01155"
                                        else:
                                            # Obtener el código de operación
                                            cod_op = datos_voucher.get('cod_op', '')
                                            cumple = True
                                            mensaje = f"Comprobante de pago validado correctamente. Código de operación: {cod_op}"
                                            
                                else:
                                    cumple = False
                                    mensaje = "El DNI en el comprobante no es válido o el documento no es visible correctamente"
                    
                    # Verificar DDJJ de plazo
                    elif codigo_documento == DJJ_PLAZO:
                        # Buscar la hoja de vida en los documentos
                        fecha_hv = None
                        for doc in documentos_candidato:
                            if doc['nombre'] == DJJ_PLAZO:
                                fecha_hv = doc.get('fecha_firma')
                                break

                        if fecha_hv:
                            try:
                                # Convertir fecha_hv a datetime
                                try:
                                    fecha_hv_dt = datetime.strptime(str(fecha_hv), '%Y-%m-%d %H:%M:%S.%f')
                                except ValueError:
                                    try:
                                        fecha_hv_dt = datetime.strptime(str(fecha_hv), '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        fecha_hv_dt = datetime.strptime(str(fecha_hv), '%Y-%m-%d')
                                
                                # Formatear la fecha para mostrar
                                fecha_hv_formateada = fecha_hv_dt.strftime('%d/%m/%Y')
                                
                                # Obtener fechas de las DDJJ
                                resultado_consentimiento = verificar_ddjj(
                                    file_name="DDJJ_DE_CONSENTIMIENTO_DE_PARTICIPACIÓN.pdf",
                                    num_expediente=num_expediente,
                                    dni=dni,
                                    id_anexo=1
                                )
                                
                                resultado_no_deuda = verificar_ddjj(
                                    file_name="DDJJ_DE_NO_TENER_DEUDA_DE_REPARACIÓN_CIVIL.pdf",
                                    num_expediente=num_expediente,
                                    dni=dni,
                                    id_anexo=2
                                )
                                
                                if "error" in resultado_consentimiento or "error" in resultado_no_deuda:
                                    cumple = None  # Estado ALERTA
                                    mensaje = "ELECCIA no pudo verificar este requisito, validar"
                                else:
                                    fecha_consentimiento_ddjj = resultado_consentimiento.get('fecha', '')
                                    fecha_no_deuda_ddjj = resultado_no_deuda.get('fecha', '')
                                    
                                    if fecha_consentimiento_ddjj and fecha_no_deuda_ddjj:
                                        try:
                                            # Normalizar formato de fechas de DDJJ
                                            fecha_consentimiento_ddjj = fecha_consentimiento_ddjj.replace('-', '/')
                                            fecha_no_deuda_ddjj = fecha_no_deuda_ddjj.replace('-', '/')
                                            
                                            # Convertir fechas de DDJJ a datetime
                                            fecha_consentimiento_dt = datetime.strptime(fecha_consentimiento_ddjj, '%d/%m/%Y')
                                            fecha_no_deuda_dt = datetime.strptime(fecha_no_deuda_ddjj, '%d/%m/%Y')
                                            
                                            # Comparar solo las fechas (ignorando la hora)
                                            fecha_hv_solo = fecha_hv_dt.date()
                                            fecha_consentimiento_solo = fecha_consentimiento_dt.date()
                                            fecha_no_deuda_solo = fecha_no_deuda_dt.date()
                                            
                                            if fecha_consentimiento_solo < fecha_hv_solo or fecha_no_deuda_solo < fecha_hv_solo:
                                                cumple = False
                                                mensaje = f"Declaración Jurada de Consentimiento completado en fecha {fecha_consentimiento_ddjj} y Declaración Jurada de No deuda completado en fecha {fecha_no_deuda_ddjj}. Ambos deben ser completados en fecha igual o posterior a {fecha_hv_formateada} de la declaración jurada de Hoja de Vida presentada"
                                            else:
                                                cumple = True
                                                mensaje = f"Declaración Jurada de Consentimiento completado en fecha {fecha_consentimiento_ddjj} y Declaración Jurada de No deuda completado en fecha {fecha_no_deuda_ddjj}. Ambos completados en fecha igual o posterior a {fecha_hv_formateada} de la declaración jurada de Hoja de Vida presentada"
                                        except ValueError as e:
                                            cumple = None
                                            mensaje = f"Eleccia detecto un formato de fecha incorrecto en las declaraciones juradas"
                                    else:
                                        cumple = None
                                        mensaje = "No se encontraron las fechas en las Declaraciones Juradas."
                            except ValueError as e:
                                cumple = None
                                mensaje = f"Eleccia detecto un formato de fecha incorrecto en la hoja de vida"
                        else:
                            cumple = None
                            mensaje = "No se encontró la fecha de la hoja de vida."
            
            return cumple, mensaje, url_documento
    
    # Si no se encontró el documento
    return cumple, mensaje, ""

def validar_documentos_obligatorios(db, id_expediente: int, id_candidato: int, documentos_candidato: list, 
                                   info_candidato: dict = None, num_expediente: str = None) -> dict:
    """
    Valida los documentos obligatorios para todos los candidatos.
    Retorna un diccionario con el estado de cada documento obligatorio.
    Utiliza ThreadPoolExecutor para procesar validaciones en paralelo de forma segura.
    """
    resultados = {}
    
    # Definir una función para ejecutar la validación de un documento
    def validar_documento(codigo_documento):
        try:
            return (
                codigo_documento,
                validar_documento_individual(
                    db, id_expediente, id_candidato, documentos_candidato, 
                    codigo_documento, info_candidato, num_expediente,
                    usar_nueva_sesion=True  # Usar sesión independiente
                )
            )
        except Exception as e:
            print(f"Error al validar documento {codigo_documento}: {str(e)}")
            return (codigo_documento, (False, f"Error interno: {str(e)}", ""))
    
    documentos_a_validar = [DDJJ_CONSENTIMIENTO, DDJJ_DEUDA_REPARACION, COMPROBANTE_PAGO, DJJ_PLAZO]
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_doc = {
            executor.submit(validar_documento, doc): doc 
            for doc in documentos_a_validar
        }
        
        for future in concurrent.futures.as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                codigo_documento, (cumple, mensaje, url) = future.result()
                
                # Mapear los resultados según el tipo de documento
                if codigo_documento == DDJJ_CONSENTIMIENTO:
                    resultados['DDJJ_CONSENTIMIENTO'] = {
                        'cumple': cumple,
                        'mensaje': mensaje,
                        'estado': 'cumple' if cumple else 'no_cumple',
                        'estado_color': 'green' if cumple else 'red',
                        'estado_texto': 'Cumple' if cumple else 'No Cumple',
                        'url_documento': url
                    }
                elif codigo_documento == DDJJ_DEUDA_REPARACION:
                    resultados['DDJJ_NO_DEUDA'] = {
                        'cumple': cumple,
                        'mensaje': mensaje,
                        'estado': 'cumple' if cumple else 'no_cumple',
                        'estado_color': 'green' if cumple else 'red',
                        'estado_texto': 'Cumple' if cumple else 'No Cumple',
                        'url_documento': url
                    }
                elif codigo_documento == COMPROBANTE_PAGO:
                    resultados['COMPROBANTE_DE_PAGO'] = {
                        'cumple': cumple,
                        'mensaje': mensaje,
                        'estado': 'cumple' if cumple else 'no_cumple',
                        'estado_color': 'green' if cumple else 'red',
                        'estado_texto': 'Cumple' if cumple else 'No Cumple',
                        'url_documento': url
                    }
                elif codigo_documento == DJJ_PLAZO:
                    resultados['DDJJ_PLAZO'] = {
                        'cumple': cumple,
                        'mensaje': mensaje,
                        'estado': 'cumple' if cumple else 'no_cumple',
                        'estado_color': 'green' if cumple else 'red',
                        'estado_texto': 'Cumple' if cumple else 'No Cumple',
                        'url_documento': url
                    }
            except Exception as e:
                print(f"Error al procesar documento {doc}: {str(e)}")
                # Añadir un resultado de error para este documento
                resultados[doc] = {
                    'cumple': False,
                    'mensaje': f"Error al procesar el documento: {str(e)}",
                    'nombre_requisito': f'Documento {doc}',
                    'estado': 'no_cumple',
                    'estado_color': 'red',
                    'estado_texto': 'Error',
                    'url_documento': ''
                }
    
    # Validar fechas de DDJJ contra fecha de entrega de hoja de vida
    try:
        import re

        # Buscar la hoja de vida en los documentos
        fecha_hv = None
        for doc in documentos_candidato:
            if doc['nombre'] == DJJ_PLAZO:
                fecha_hv = doc.get('fecha_firma')
                break

        if fecha_hv:
            try:
                # Inicializar cumple_fechas como True por defecto
                cumple_fechas = True
                
                # Convertir fecha_hv a datetime (formato de base de datos)
                # Intentar diferentes formatos de fecha
                try:
                    fecha_hv_dt = datetime.strptime(str(fecha_hv), '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        fecha_hv_dt = datetime.strptime(str(fecha_hv), '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        fecha_hv_dt = datetime.strptime(str(fecha_hv), '%Y-%m-%d')
                
                # Convertir a formato dd/mm/yyyy para mostrar
                fecha_hv_formateada = fecha_hv_dt.strftime('%d/%m/%Y')
                
                # Buscar las DDJJ en los documentos
                ddjj_consentimiento = None
                ddjj_no_deuda = None
                
                for doc in documentos_candidato:
                    if doc['nombre'] == DDJJ_CONSENTIMIENTO:
                        ddjj_consentimiento = doc
                    elif doc['nombre'] == DDJJ_DEUDA_REPARACION:
                        ddjj_no_deuda = doc
                
                if ddjj_consentimiento and ddjj_no_deuda:
                    # Obtener fechas de las DDJJ desde verificar_ddjj (una sola llamada por DDJJ)
                    resultado_consentimiento = verificar_ddjj(
                        file_name="DDJJ_DE_CONSENTIMIENTO_DE_PARTICIPACIÓN.pdf",
                        num_expediente=num_expediente,
                        dni=info_candidato.get('tx_dni'),
                        id_anexo=1
                    )
                    
                    resultado_no_deuda = verificar_ddjj(
                        file_name="DDJJ_DE_NO_TENER_DEUDA_DE_REPARACIÓN_CIVIL.pdf",
                        num_expediente=num_expediente,
                        dni=info_candidato.get('tx_dni'),
                        id_anexo=2
                    )
                    
                    fecha_consentimiento_ddjj = resultado_consentimiento.get('fecha', '')
                    fecha_no_deuda_ddjj = resultado_no_deuda.get('fecha', '')
                    
                    if fecha_consentimiento_ddjj and fecha_no_deuda_ddjj:
                        try:
                            # Normalizar formato de fechas de DDJJ (convertir - a /)
                            fecha_consentimiento_ddjj = fecha_consentimiento_ddjj.replace('-', '/')
                            fecha_no_deuda_ddjj = fecha_no_deuda_ddjj.replace('-', '/')
                            
                            # Convertir fechas de DDJJ a datetime
                            fecha_consentimiento_dt = datetime.strptime(fecha_consentimiento_ddjj, '%d/%m/%Y')
                            fecha_no_deuda_dt = datetime.strptime(fecha_no_deuda_ddjj, '%d/%m/%Y')
                            
                            # Comparar solo las fechas (ignorando la hora)
                            fecha_hv_solo = fecha_hv_dt.date()
                            fecha_consentimiento_solo = fecha_consentimiento_dt.date()
                            fecha_no_deuda_solo = fecha_no_deuda_dt.date()
                            
                            if fecha_consentimiento_solo < fecha_hv_solo or fecha_no_deuda_solo < fecha_hv_solo:
                                cumple_fechas = False
                                mensaje_fechas = f"DDJJ_CONSENTIMIENTO firmado en fecha {fecha_consentimiento_ddjj} y DDJJ_DEUDA_REPARACION firmado en fecha {fecha_no_deuda_ddjj}. Ambos deben ser firmados en fecha igual o posterior a {fecha_hv_formateada}"
                            else:
                                cumple_fechas = True
                                mensaje_fechas = f"DDJJ_CONSENTIMIENTO firmado en fecha {fecha_consentimiento_ddjj} y DDJJ_DEUDA_REPARACION firmado en fecha {fecha_no_deuda_ddjj}. Ambos firmados en fecha igual o posterior a {fecha_hv_formateada}"
                        except ValueError as e:
                            cumple_fechas = None
                            mensaje_fechas = f"Eleccia detecto un formato de fecha incorrecto en las declaraciones juradas"
                    else:
                        cumple_fechas = None
                        mensaje_fechas = "No se encontraron las fechas en las Declaraciones Juradas."
                else:
                    cumple_fechas = False
                    mensaje_fechas = "No se encontraron las Declaraciones Juradas necesarias."
            except ValueError as e:
                cumple_fechas = None
                mensaje_fechas = f"Eleccia detecto un formato de fecha incorrecto en la hoja de vida"
        else:
            cumple_fechas = None
            mensaje_fechas = "No se encontró la fecha de la hoja de vida."

            # Actualizar el resultado de DDJJ_PLAZO con la validación de fechas
            if 'DDJJ_PLAZO' in resultados:
                resultados['DDJJ_PLAZO'].update({
                    'cumple': cumple_fechas,
                    'mensaje': mensaje_fechas,
                    'estado': 'cumple' if cumple_fechas else 'no_cumple',
                    'estado_color': 'green' if cumple_fechas else 'red',
                    'estado_texto': 'Cumple' if cumple_fechas else 'No Cumple'
                })

    except Exception as e:
        print(f"Error en la validación de fechas: {str(e)}")
        if 'DDJJ_PLAZO' in resultados:
            resultados['DDJJ_PLAZO'].update({
                'cumple': False,
                'mensaje': f"Error en la validación de fechas: {str(e)}",
                'estado': 'no_cumple',
                'estado_color': 'red',
                'estado_texto': 'Error'
            })
    
    return resultados

def validar_documentos_condicionales(db, id_expediente: int, id_candidato: int, 
                                    documentos_candidato: list, info_candidato: dict) -> dict:
    """
    Valida los documentos condicionales basados en la información del candidato.
    Ahora también usa sesiones independientes para cada validación.
    """
    resultados = {}
    
    # Verificar si es extranjero
    if info_candidato.get('tx_pais_nacimiento', 'PERÚ').upper() != 'PERÚ':
        cumple_extranjero, mensaje_extranjero, url_extranjero = validar_documento_individual(
            db, id_expediente, id_candidato, documentos_candidato, DDJJ_EXTRANJERO, 
            info_candidato, usar_nueva_sesion=True
        )
        resultados['DDJJ_INSCRIPCION_EXTRANJERO'] = {
            'cumple': cumple_extranjero,
            'mensaje': mensaje_extranjero,
            'nombre_requisito': 'Declaración jurada de constancia de inscripción para extranjero',
            'estado': 'cumple' if cumple_extranjero else 'no_cumple',
            'estado_color': 'green' if cumple_extranjero else 'red',
            'estado_texto': 'Cumple' if cumple_extranjero else 'No Cumple',
            'url_documento': url_extranjero
        }
    
    # Verificar si el ubigeo de domicilio es diferente al de postulación
    if info_candidato.get('tx_ubigeo') != info_candidato.get('tx_ubigeo_postula'):
        cumple_domicilio, mensaje_domicilio, url_domicilio = validar_documento_individual(
            db, id_expediente, id_candidato, documentos_candidato, DDJJ_DOMICILIO_MULTIPLE, 
            info_candidato, usar_nueva_sesion=True
        )
        resultados['DDJJ_DOMICILIO_MULTIPLE'] = {
            'cumple': cumple_domicilio,
            'mensaje': mensaje_domicilio,
            'nombre_requisito': 'Declaración jurada de domicilio múltiple',
            'estado': 'cumple' if cumple_domicilio else 'no_cumple',
            'estado_color': 'green' if cumple_domicilio else 'red',
            'estado_texto': 'Cumple' if cumple_domicilio else 'No Cumple',
            'url_documento': url_domicilio
        }
    
    return resultados

def validar_ubigeo_candidato(db, id_expediente: int, id_candidato: int, info_candidato: dict, url_documento: str = None) -> tuple[bool, str, str]:
    """
    Valida si el ubigeo de vivienda del candidato corresponde al ubigeo de postulación.
    
    Args:
        db: Sesión de base de datos
        id_expediente: ID del expediente
        id_candidato: ID del candidato
        info_candidato: Información del candidato
        url_documento: URL del documento de domicilio múltiple (opcional)
    
    Returns:
        Tuple con (cumple, mensaje, url_documento)
    """
    ubigeo_vivienda = info_candidato.get('tx_ubigeo', '')
    ubigeo_postula = info_candidato.get('tx_ubigeo_postula', '')
    
    if not ubigeo_vivienda or not ubigeo_postula:
        cumple = False
        mensaje = "Falta información de ubigeo"
    else:
        cumple = ubigeo_vivienda == ubigeo_postula
        if cumple:
            mensaje = "El ubigeo de vivienda coincide con el ubigeo de postulación"
        else:
            # Si los ubigeos no coinciden, debe existir el documento de domicilio múltiple
            if url_documento:
                mensaje = f"El ubigeo de vivienda ({ubigeo_vivienda}) no coincide con el ubigeo de postulación ({ubigeo_postula}), pero se presenta documento de acreditación de domicilio múltiple"
                cumple = True  # Con el documento de domicilio múltiple, cumple con el requisito
            else:
                mensaje = f"El ubigeo de vivienda ({ubigeo_vivienda}) no coincide con el ubigeo de postulación ({ubigeo_postula}) y no se presenta documento de acreditación de domicilio múltiple"
                cumple = False
    
    return cumple, mensaje, url_documento if url_documento else ""

def validar_afiliacion_rop(db, id_expediente: int, id_candidato: int, info_candidato: dict) -> tuple[bool, str]:
    """
    Valida si el candidato está afiliado al partido político por el que postula.
    """
    from app.libraries.lb_utils import verificar_rop

    dni = info_candidato.get('tx_dni', '')
    nombre_candidato = f"{info_candidato.get('tx_nombres', '')} {info_candidato.get('tx_apellidos', '')}".upper()
    cargo_postulado = info_candidato.get('tx_cargo_eleccion', '').upper()
    partido_politico = info_candidato.get('tx_organizacion_politica', '')

    if not dni or not partido_politico:
        cumple = False
        mensaje = "No se puede validar: Falta información de DNI o partido político"
    else:
        # Verificar afiliación en el ROP
        resultado_rop = verificar_rop(dni, partido_politico, nombre_candidato, cargo_postulado)
        cumple = resultado_rop.get('afiliado', False)
        mensaje = resultado_rop.get('mensaje', "Error al verificar afiliación")

    return cumple, mensaje

def obtener_id_candidato(db, dni: str) -> int:
    """
    Obtiene el ID del candidato en la base de datos ELECCIA a partir del DNI.
    """
    try:
        candidato = db.query(Candidato).filter(Candidato.dni == dni).first()
        return candidato.id_candidato if candidato else None
    except Exception as e:
        print(f"Error al obtener ID de candidato: {str(e)}")
        return None

def validar_hoja_vida_candidato(db, id_expediente: int, dni_candidato: str, info_candidato: dict, documentos_candidato: list, num_expediente: str = None) -> dict:
    """
    Valida la hoja de vida de un candidato específico.
    Utiliza paralelismo para ejecutar validaciones independientes simultáneamente.
    """
    # Obtener ID del candidato
    id_candidato = obtener_id_candidato(db, dni_candidato)
    if not id_candidato:
        return {"error": "No se encontró el ID del candidato en la base de datos"}
    
    # Función para ejecutar validación de documentos obligatorios
    def ejecutar_validacion_obligatorios():
        return validar_documentos_obligatorios(db, id_expediente, id_candidato, documentos_candidato, info_candidato, num_expediente)
    
    # Función para ejecutar validación de documentos condicionales
    def ejecutar_validacion_condicionales():
        return validar_documentos_condicionales(db, id_expediente, id_candidato, documentos_candidato, info_candidato)
    
    # Función para ejecutar validación de ubigeo
    def ejecutar_validacion_ubigeo():
        # Buscar el documento de domicilio múltiple en la lista
        url_domicilio_multiple = ""
        for doc in documentos_candidato:
            if doc['nombre'] == DDJJ_DOMICILIO_MULTIPLE:
                url_domicilio_multiple = doc.get('url', '')
                break
        
        # Validar ubigeo incluyendo la URL del documento si existe
        cumple_ubigeo, mensaje_ubigeo, url_documento = validar_ubigeo_candidato(
            db=db, 
            id_expediente=id_expediente, 
            id_candidato=id_candidato, 
            info_candidato=info_candidato, 
            url_documento=url_domicilio_multiple
        )
        
        return {
            'UBIGEO_CANDIDATO': {
                'cumple': cumple_ubigeo,
                'mensaje': mensaje_ubigeo,
                'nombre_requisito': 'El domicilio del candidato corresponde al ubigeo al que postula',
                'estado': 'cumple' if cumple_ubigeo else 'no_cumple',
                'estado_color': 'green' if cumple_ubigeo else 'red',
                'estado_texto': 'Cumple' if cumple_ubigeo else 'No Cumple',
                'url_documento': url_documento  # Usar la URL retornada por la función
            }
        }

    
    # Función para ejecutar validación de ROP
    def ejecutar_validacion_rop():
        cumple_rop, mensaje_rop = validar_afiliacion_rop(db, id_expediente, id_candidato, info_candidato)
        return {
            'VERIFICA_ROP': {
                'cumple': cumple_rop,
                'mensaje': mensaje_rop,
                'nombre_requisito': 'Afiliación al partido político en el ROP',
                'estado': 'cumple' if cumple_rop else 'no_cumple',
                'estado_color': 'green' if cumple_rop else 'red',
                'estado_texto': 'Cumple' if cumple_rop else 'No Cumple',
                'url_documento': ''  # No hay documento para la afiliación ROP
            }
        }
    
    # Ejecutar validaciones en paralelo usando ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_obligatorios = executor.submit(ejecutar_validacion_obligatorios)
        future_condicionales = executor.submit(ejecutar_validacion_condicionales)
        future_ubigeo = executor.submit(ejecutar_validacion_ubigeo)
        future_rop = executor.submit(ejecutar_validacion_rop)
        
        # Recopilar resultados cuando estén disponibles
        resultados_obligatorios = future_obligatorios.result()
        resultados_condicionales = future_condicionales.result()
        resultados_ubigeo = future_ubigeo.result()
        resultados_rop = future_rop.result()
    
    # Combinar todos los resultados
    resultados = {**resultados_obligatorios, **resultados_condicionales, **resultados_ubigeo, **resultados_rop}
    
    # Determinar el estado general
    cumple_general = all(estado['cumple'] for estado in resultados.values())
    
    return {
        'cumple': cumple_general,
        'requisitos': resultados
    }

def validar_requisitos_hoja_vida(num_expediente: str, info_candidatos: dict, documentos_candidatos: dict) -> dict:
    """
    Valida los requisitos de hoja de vida para todos los candidatos en paralelo.
    """
    resultados = {}
    db = next(get_db())

    # Obtener ID de expediente
    id_expediente = obtener_id_expediente_eleccia(db, num_expediente)
    if not id_expediente:
        return {"error": "No se encontró el expediente"}
    
    # Crear una función para validar un candidato
    def validar_candidato(dni):
        try:
            candidatos = info_candidatos.get('CANDIDATOS', {}).get(dni, [])
            if not candidatos:
                return dni, {"error": f"No se encontró información para el candidato con DNI {dni}"}
            
            candidato = candidatos[0]  # Tomamos el primer registro del candidato
            
            # Obtener documentos del candidato
            documentos = documentos_candidatos.get(dni, [])
            
            # Verificar que documentos sea una lista
            if not isinstance(documentos, list):
                print(f"Advertencia: documentos para candidato {dni} no es una lista: {documentos}")
                documentos = []
            
            # Procesar cada documento para asegurar que tenga la estructura correcta
            documentos_procesados = []
            for doc in documentos:
                if isinstance(doc, dict):
                    # Si ya tiene la estructura correcta, usarlo tal cual
                    documentos_procesados.append(doc)
                else:
                    # Si es un string, asumir que es el nombre del documento
                    documentos_procesados.append({
                        "nombre": doc,
                        "url": ""  # URL vacía si no se proporciona
                    })
            
            # Crear una nueva sesión de DB para cada candidato para evitar problemas de concurrencia
            with next(get_db()) as db_candidato:
                resultado = validar_hoja_vida_candidato(
                    db=db_candidato,
                    id_expediente=id_expediente,
                    dni_candidato=dni,
                    info_candidato=candidato,
                    documentos_candidato=documentos_procesados,
                    num_expediente=num_expediente
                )
                
                return dni, {
                    'cumple': resultado['cumple'],
                    'requisitos': resultado['requisitos'],
                    'info_candidato': candidato,
                    'documentos': documentos_procesados
                }
        except Exception as e:
            return dni, {"error": f"Error al validar candidato {dni}: {str(e)}"}
    
    # Lista de DNIs de candidatos
    dnis = list(info_candidatos.get('CANDIDATOS', {}).keys())
    
    # Validar candidatos en paralelo
    with ThreadPoolExecutor(max_workers=min(10, len(dnis))) as executor:
        future_to_dni = {executor.submit(validar_candidato, dni): dni for dni in dnis}
        
        for future in concurrent.futures.as_completed(future_to_dni):
            try:
                dni, resultado = future.result()
                resultados[dni] = resultado
            except Exception as e:
                dni = future_to_dni[future]
                resultados[dni] = {"error": f"Error en procesamiento para DNI {dni}: {str(e)}"}
    
    return resultados

