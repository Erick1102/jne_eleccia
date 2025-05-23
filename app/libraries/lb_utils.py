import os
from docx import Document
from sqlalchemy.sql import func

from app.database.models.db_models_eleccia import Expediente, Candidato, Estado
from app.database.db_scripts import Expediente_sije, Consulta_ROP
from app.database.db_session import SessionLocal

def crear_carpetas(num_expediente, BASE_PATH_DOCUMENTOS):
    """
    Crea la estructura de carpetas necesaria para almacenar los documentos del expediente.
    
    :param num_expediente: El número del expediente.
    :param base_path_documentos: Ruta base donde se almacenarán los documentos.
    :return: Ruta de las carpetas creadas.
    """
    # Crear la carpeta principal del expediente
    expediente_path = os.path.join(BASE_PATH_DOCUMENTOS, str(num_expediente))
    os.makedirs(expediente_path, exist_ok=True)

    # Crear subcarpetas para documentos de expediente y documentos de candidatos
    documentos_path = os.path.join(expediente_path, "documentos_expediente")
    os.makedirs(documentos_path, exist_ok=True)
    
    candidatos_path = os.path.join(expediente_path, "documentos_candidato")
    os.makedirs(candidatos_path, exist_ok=True)
    
    resolucion_path = os.path.join(expediente_path, "resoluciones")
    os.makedirs(candidatos_path, exist_ok=True)

    return expediente_path, documentos_path, candidatos_path

def validar_expediente(num_expediente: str, tipo_expediente: int, tipo_materia: int) -> dict:
    """
    Valida si el expediente pertenece al tipo de materia especificado y obtiene información adicional.
    
    Args:
        num_expediente: Número de expediente a validar
        tipo_expediente: Tipo de expediente en ELECCIA (1: inscripción, 2: apelación, etc)
        tipo_materia: Tipo de materia en ELECCIA (1: lista, 2: candidato, etc)
        
    Returns:
        dict: Diccionario con información del expediente o None si no es válido
    """
    from app.database.db_session import SessionLocal
    db_session = SessionLocal()
    
    try:
        # Mapeo de tipos de expediente y materia entre sistemas ELECCIA -> SIJE
        mapeo_tipo_expediente = {
            1: 13,  # Si en ELECCIA es 1, en SIJE es 13
        }
        
        mapeo_tipo_materia = {
            5: 27,  # Si en ELECCIA es 5, en SIJE es 27
        }
        
        # Obtener los IDs correspondientes en SIJE
        tipo_expediente_sije = mapeo_tipo_expediente.get(tipo_expediente)
        tipo_materia_sije = mapeo_tipo_materia.get(tipo_materia)
        
        if not tipo_expediente_sije or not tipo_materia_sije:
            raise ValueError("No existe mapeo para el tipo de expediente o materia proporcionado")
        
        # Buscar expediente en SIJE
        expediente_sije = buscar_expediente_sije(num_expediente)
        
        if not expediente_sije:
            raise ValueError(f"No se encontró el expediente {num_expediente} en SIJE")
        
        # Verificar que el expediente corresponda al tipo y materia especificados
        if expediente_sije['IDTIPOEXPEDIENTE'] != tipo_expediente_sije or expediente_sije['IDMATERIA'] != tipo_materia_sije:
            raise ValueError(f"El expediente no corresponde al tipo de expediente y materia especificados. "
                            f"Esperado: tipo={tipo_expediente_sije}, materia={tipo_materia_sije}. "
                            f"Encontrado: tipo={expediente_sije['IDTIPOEXPEDIENTE']}, materia={expediente_sije['IDMATERIA']}")
        
        # Verificar si el expediente ya existe en ELECCIA
        expediente_existente = db_session.query(Expediente).filter(
            Expediente.nombre_expediente == num_expediente
        ).first()
        
        if expediente_existente:
            # Cambiar el estado a PENDIENTE (3) si ya existe
            expediente_existente.id_estado = 3
            expediente_existente.modificado_por = 'ADMIN'
            expediente_existente.modificado_en = func.current_timestamp()
            db_session.commit()
            
            return {
                'id_expediente_sije': expediente_sije['IDEXPEDIENTE'],
                'tipo_expediente': tipo_expediente,
                'tipo_materia': tipo_materia,
                'usuario_asignado': expediente_existente.usuario_asignado
            }
        
        # Preparar la información para guardar en ELECCIA
        expediente_info = {
            'id_expediente_sije': expediente_sije['IDEXPEDIENTE'],
            'tipo_expediente': tipo_expediente,  
            'tipo_materia': tipo_materia,        
            'usuario_asignado': 'ADMIN'          # Valor por defecto
        }
        
        # Almacenar datos del expediente en esquema ELECCIA solo si no existe
        nuevo_expediente = Expediente(
            numero_expediente=str(expediente_info['id_expediente_sije']),
            nombre_expediente=num_expediente,
            id_tipo_expediente=tipo_expediente,
            id_materia=tipo_materia,
            id_estado=3,  # PENDIENTE
            usuario_asignado=expediente_info['usuario_asignado'],
            creado_por=expediente_info['usuario_asignado']
        )
        
        db_session.add(nuevo_expediente)
        db_session.commit()
        
        return expediente_info
        
    except Exception as e:
        db_session.rollback()
        raise ValueError(f"Error al validar/guardar el expediente: {str(e)}")
    finally:
        db_session.close()
        
def buscar_expediente_sije(num_expediente: str) -> dict:
    """
    Busca el expediente en la base de datos SIJE y valida que corresponda al tipo y materia.
    
    """
    db = SessionLocal()
    try:
        resultados = db.execute(Expediente_sije, {"TXCODEXPEDIENTEEXT": num_expediente}).fetchall()
        
        if not resultados:
            return None
            
        # Convertir el resultado a diccionario
        expediente = {
            'IDEXPEDIENTE': resultados[0][0],
            'IDMATERIA': resultados[0][1],
            'IDTIPOEXPEDIENTE': resultados[0][2]
        }
        
        return expediente
    
    except Exception as e:
        print(f"Error al consultar SIJE: {str(e)}")
        return None
    finally:
        db.close()

def obtener_id_expediente_eleccia(db, num_expediente: str) -> int:
    """
    Obtiene el ID del expediente en el esquema ELECCIA a partir del número de expediente.
    """
    try:
        expediente = db.query(Expediente).filter(
            Expediente.nombre_expediente == num_expediente
        ).first()
        
        if expediente:
            return expediente.id_expediente
        else:
            return None
    except Exception as e:
        print(f"Error al obtener ID de expediente: {str(e)}")
        return None

def verificar_estado_requisito(db, id_expediente: int, codigo_requisito: str, tipo_requisito: str = 'GENERAL', id_candidato: int = None) -> tuple[bool, bool, str, str]:
    """
    Verifica si un requisito ya está guardado en la base de datos.
    
    Args:
        db: Sesión de base de datos
        id_expediente: ID del expediente
        codigo_requisito: Código del requisito a verificar
        tipo_requisito: Tipo de requisito ('LISTA', 'CANDIDATO', 'ACTA', 'PLAN_GOB', 'GENERAL')
        id_candidato: ID del candidato (opcional, solo para requisitos tipo 'CANDIDATO')
        
    Returns:
        Tuple con (existe, cumple, mensaje, url_documento)
    """
    from app.database.models.db_models_eleccia import ConfiguracionRequisito, Requisito, EstadoRequisitoExpediente
    
    # Obtener la configuración del requisito
    configuracion = db.query(ConfiguracionRequisito).join(
        Requisito, 
        ConfiguracionRequisito.id_requisito == Requisito.id_requisito
    ).filter(
        Requisito.codigo_requisito == codigo_requisito
    ).first()
    
    if not configuracion:
        return False, None, None, None
    
    # Construir el filtro base
    filtro = [
        EstadoRequisitoExpediente.id_expediente == id_expediente,
        EstadoRequisitoExpediente.id_configuracion == configuracion.id_configuracion,
        EstadoRequisitoExpediente.tipo_requisito == tipo_requisito
    ]
    
    # Agregar filtro de candidato si es necesario
    if tipo_requisito == 'CANDIDATO' and id_candidato is not None:
        filtro.append(EstadoRequisitoExpediente.id_candidato == id_candidato)
    
    # Buscar el estado del requisito
    estado_requisito = db.query(EstadoRequisitoExpediente).filter(*filtro).first()
    
    if estado_requisito:
        cumple = estado_requisito.id_estado_validacion == 7  # 7 = CUMPLE
        return True, cumple, estado_requisito.observaciones, estado_requisito.archivo_ruta
    
    return False, None, None, None

def actualizar_estado_requisito(db, id_expediente: int, codigo_requisito: str, cumple: bool, mensaje: str, 
                               usuario: str, archivo_ruta: str = None, id_candidato: int = None, 
                               tipo_requisito: str = 'GENERAL', nueva_sesion: bool = False):
    """
    Actualiza el estado de un requisito en la base de datos ELECCIA.
    Optimizado para operaciones concurrentes.
    
    Args:
        db: Sesión de base de datos
        id_expediente: ID del expediente
        codigo_requisito: Código del requisito a actualizar
        cumple: Si el requisito cumple o no
        mensaje: Mensaje descriptivo del resultado
        usuario: Usuario que realiza la actualización
        archivo_ruta: Ruta del archivo asociado (opcional)
        id_candidato: ID del candidato (opcional)
        tipo_requisito: Tipo de requisito (por defecto 'GENERAL')
        nueva_sesion: Si es True, crea una nueva sesión para esta operación
    """
    from app.database.models.db_models_eleccia import (
        EstadoRequisitoExpediente, 
        Estado, 
        ConfiguracionRequisito, 
        Requisito
    )
    from sqlalchemy.orm import aliased
    from app.database.db_session import get_db, SessionLocal
    from sqlalchemy import func, and_
    import threading
    import time
    
    # Cache para estados y configuraciones
    _estado_cache = {}
    _config_cache = {}
    _cache_lock = threading.Lock()
    
    # Si se solicita una nueva sesión, crear una
    if nueva_sesion:
        session_to_use = SessionLocal()
        own_session = True
    else:
        session_to_use = db
        own_session = False
    
    try:
        # Obtener el ID del estado correspondiente (usando caché)
        estado_key = 'CUMPLE' if cumple is True else 'NO_CUMPLE' if cumple is False else 'ALERTA'
        with _cache_lock:
            if estado_key not in _estado_cache:
                estado_id = session_to_use.query(Estado.id_estado).filter(
                    Estado.codigo_estado == estado_key
                ).scalar()
                _estado_cache[estado_key] = estado_id
            else:
                estado_id = _estado_cache[estado_key]
        
        if not estado_id:
            raise ValueError(f"No se encontró el estado {estado_key}")
        
        # Obtener la configuración de requisito (usando caché)
        with _cache_lock:
            if codigo_requisito not in _config_cache:
                configuracion = session_to_use.query(ConfiguracionRequisito).join(
                    Requisito, 
                    ConfiguracionRequisito.id_requisito == Requisito.id_requisito
                ).filter(
                    Requisito.codigo_requisito == codigo_requisito
                ).first()
                _config_cache[codigo_requisito] = configuracion
            else:
                configuracion = _config_cache[codigo_requisito]
        
        if not configuracion:
            print(f"No se encontró configuración para el requisito: {codigo_requisito}")
            if own_session:
                session_to_use.close()
            return
        
        # Asegurarse de que archivo_ruta no sea None
        archivo_ruta = archivo_ruta or ''
        
        # Buscar si ya existe un estado para este requisito
        estado_requisito = session_to_use.query(EstadoRequisitoExpediente).filter(
            and_(
                EstadoRequisitoExpediente.id_expediente == id_expediente,
                EstadoRequisitoExpediente.id_configuracion == configuracion.id_configuracion,
                EstadoRequisitoExpediente.tipo_requisito == tipo_requisito,
                EstadoRequisitoExpediente.id_candidato == id_candidato
            )
        ).first()
        
        if estado_requisito:
            # Actualizar el registro existente
            estado_requisito.id_estado_validacion = estado_id
            estado_requisito.observaciones = mensaje
            estado_requisito.validacion_anterior = estado_requisito.validado_por
            estado_requisito.modificado_por = usuario
            estado_requisito.validado_por = usuario
            estado_requisito.fecha_modificacion = func.current_timestamp()
            estado_requisito.archivo_ruta = archivo_ruta
        else:
            # Crear nuevo estado
            estado_requisito = EstadoRequisitoExpediente(
                id_expediente=id_expediente,
                id_configuracion=configuracion.id_configuracion,
                id_candidato=id_candidato,
                tipo_requisito=tipo_requisito,
                id_estado_validacion=estado_id,
                validacion_anterior=None,
                creado_por=usuario,
                validado_por=usuario,
                modificado_por=None,
                observaciones=mensaje,
                archivo_ruta=archivo_ruta
            )
            session_to_use.add(estado_requisito)
        
        # Intentar guardar con reintentos
        max_intentos = 3
        intento = 0
        while intento < max_intentos:
            try:
                session_to_use.commit()
                break
            except Exception as e:
                intento += 1
                if intento == max_intentos:
                    raise
                print(f"Error al guardar (intento {intento}): {str(e)}")
                session_to_use.rollback()
                time.sleep(0.1)  # Pequeña pausa antes de reintentar
                
                # Reintentar la operación con una nueva sesión
                if own_session:
                    session_to_use.close()
                    session_to_use = SessionLocal()
                
                try:
                    estado_requisito = session_to_use.query(EstadoRequisitoExpediente).filter(
                        and_(
                            EstadoRequisitoExpediente.id_expediente == id_expediente,
                            EstadoRequisitoExpediente.id_configuracion == configuracion.id_configuracion,
                            EstadoRequisitoExpediente.tipo_requisito == tipo_requisito,
                            EstadoRequisitoExpediente.id_candidato == id_candidato
                        )
                    ).first()
                    
                    if estado_requisito:
                        estado_requisito.id_estado_validacion = estado_id
                        estado_requisito.observaciones = mensaje
                        estado_requisito.validacion_anterior = estado_requisito.validado_por
                        estado_requisito.modificado_por = usuario
                        estado_requisito.validado_por = usuario
                        estado_requisito.fecha_modificacion = func.current_timestamp()
                        estado_requisito.archivo_ruta = archivo_ruta
                    else:
                        estado_requisito = EstadoRequisitoExpediente(
                            id_expediente=id_expediente,
                            id_configuracion=configuracion.id_configuracion,
                            id_candidato=id_candidato,
                            tipo_requisito=tipo_requisito,
                            id_estado_validacion=estado_id,
                            validacion_anterior=None,
                            creado_por=usuario,
                            validado_por=usuario,
                            modificado_por=None,
                            observaciones=mensaje,
                            archivo_ruta=archivo_ruta
                        )
                        session_to_use.add(estado_requisito)
                    
                    session_to_use.commit()
                except Exception as e2:
                    print(f"Error al reintentar guardar (intento {intento}): {str(e2)}")
                    session_to_use.rollback()
                    if intento == max_intentos:
                        raise
        
    except Exception as e:
        session_to_use.rollback()
        print(f"Error al actualizar estado de requisito: {str(e)}")
        raise
    finally:
        if own_session:
            session_to_use.close()

def guardar_candidatos_eleccia(db, candidatos: dict) -> dict:
    """
    Guarda los candidatos en la base de datos ELECCIA.
    
    Args:
        db: Sesión de base de datos
        candidatos: Diccionario con la información de los candidatos
        num_expediente: Número de expediente (opcional)
        
    Returns:
        Diccionario con el resultado de la operación
    """    
    try:
        if not candidatos or 'CANDIDATOS' not in candidatos:
            return {"error": "No se encontraron candidatos para guardar"}
            
        # Obtener el estado activo por defecto
        estado_activo = db.query(Estado).filter(Estado.codigo_estado == 'ACTIVO').first()
        if not estado_activo:
            return {"error": "No se encontró el estado activo en la base de datos"}
            
        candidatos_guardados = []
        errores = []
        
        # Procesar cada candidato
        for dni, candidatos_dni in candidatos['CANDIDATOS'].items():
            for candidato in candidatos_dni:
                try:
                    # Verificar si el candidato ya existe
                    candidato_existente = db.query(Candidato).filter(Candidato.dni == dni).first()
                    
                    if candidato_existente:
                        # Actualizar datos del candidato existente
                        candidato_existente.nombres = candidato['tx_nombres']
                        candidato_existente.apellidos = candidato['tx_apellidos']
                        candidato_existente.sexo = candidato['tx_sexo']
                        candidato_existente.fecha_nacimiento = candidato['tx_fecha_nac']
                        candidato_existente.direccion = candidato['tx_domicilio']
                        candidato_existente.ubigeo = candidato['tx_ubigeo']
                        candidato_existente.puesto_postula = candidato['tx_cargo_eleccion']
                        candidato_existente.numero_lista = candidato['tx_nuposicion']
                        candidato_existente.id_estado = estado_activo.id_estado
                        candidato_existente.modificado_por = 'SISTEMA'
                        candidato_existente.fecha_modificacion = func.current_timestamp()
                    else:
                        # Crear nuevo candidato
                        nuevo_candidato = Candidato(
                            dni=dni,
                            nombres=candidato['tx_nombres'],
                            apellidos=candidato['tx_apellidos'],
                            sexo=candidato['tx_sexo'],
                            fecha_nacimiento=candidato['tx_fecha_nac'],
                            direccion=candidato['tx_domicilio'],
                            ubigeo=candidato['tx_ubigeo'],
                            puesto_postula=candidato['tx_cargo_eleccion'],
                            numero_lista=candidato['tx_nuposicion'],
                            id_estado=estado_activo.id_estado,
                            creado_por='SISTEMA'
                        )
                        db.add(nuevo_candidato)
                    
                    candidatos_guardados.append(dni)
                    
                except Exception as e:
                    errores.append(f"Error al guardar candidato {dni}: {str(e)}")
                    
        # Confirmar cambios en la base de datos
        db.commit()
        
        return {
            "mensaje": f"Se guardaron {len(candidatos_guardados)} candidatos exitosamente",
            "candidatos_guardados": candidatos_guardados,
            "errores": errores
        }
        
    except Exception as e:
        db.rollback()
        return {"error": f"Error al guardar candidatos: {str(e)}"}

def verificar_rop(dni: str, partido_politico: str, candidato, cargo_postulado: str) -> dict:
    """
    Verifica si un candidato está afiliado a un partido político específico en el ROP.
    Para Alcalde Distrital, debe estar inscrito al partido político.
    Para otros cargos, puede estar inscrito al partido o no tener afiliación.

    Args:
        dni: DNI del candidato a verificar
        partido_politico: Nombre del partido político a comparar
        candidato: Nombre del candidato
        cargo_postulado: Cargo al que postula el candidato

    Returns:
        dict: Diccionario con el resultado de la verificación
    """
    import cx_Oracle
    from app.database.db_session import engine_rop
    import time
    
    max_intentos = 3
    intento = 0
    
    while intento < max_intentos:
        try:
            # Crear una nueva conexión para cada intento
            connection = engine_rop.raw_connection()
            cursor = connection.cursor()
            
            # Crear el cursor de salida
            out_cursor = cursor.var(cx_Oracle.CURSOR)
            
            # Llamar al procedimiento almacenado
            cursor.callproc("COMPARTIDO.PKG_AFILIACION_RRHH.SP_LISTAR_CONS4ANOS_DNI", [dni, out_cursor])
            
            # Obtener resultados
            resultados_cursor = out_cursor.getvalue()
            resultados = resultados_cursor.fetchall()
            
            # Si no hay resultados, verificar según el cargo
            if not resultados:
                if cargo_postulado == "ALCALDE DISTRITAL":
                    return {
                        "afiliado": False,
                        "mensaje": f"El candidato {candidato} debe estar inscrito al partido político {partido_politico} para postular como Alcalde Distrital"
                    }
                else:
                    return {
                        "afiliado": True,
                        "mensaje": f"El candidato {candidato} no tiene afiliación a ningún partido político"
                    }
            
            # Verificar afiliaciones activas
            afiliaciones_activas = []
            for afiliacion in resultados:
                if afiliacion[4] == 'Sí':
                    afiliaciones_activas.append(afiliacion[6].strip().upper())
            
            # Caso especial para Alcalde Distrital
            if cargo_postulado == "ALCALDE DISTRITAL":
                if partido_politico.strip().upper() in afiliaciones_activas:
                    return {
                        "afiliado": True,
                        "mensaje": f"El candidato {candidato} está afiliado al partido político {partido_politico}"
                    }
                else:
                    return {
                        "afiliado": False,
                        "mensaje": f"El candidato {candidato} debe estar inscrito al partido político {partido_politico} para postular como Alcalde Distrital, se encuentra afiliado a {afiliaciones_activas}"
                    }
            
            # Para otros cargos
            if partido_politico.strip().upper() in afiliaciones_activas:
                return {
                    "afiliado": True,
                    "mensaje": f"El candidato {candidato} está afiliado al partido político {partido_politico}"
                }
            elif not afiliaciones_activas:
                return {
                    "afiliado": True,
                    "mensaje": f"El candidato {candidato} no tiene afiliación a ningún partido político"
                }
            else:
                partidos_afiliados = ", ".join(afiliaciones_activas)
                return {
                    "afiliado": False,
                    "mensaje": f"El candidato {candidato} está afiliado a otros partidos políticos: {partidos_afiliados}"
                }
                
        except Exception as e:
            intento += 1
            print(f"Intento {intento} fallido: {str(e)}")
            
            if intento == max_intentos:
                return {
                    "afiliado": False,
                    "mensaje": f"Error al verificar afiliación después de {max_intentos} intentos: {str(e)}"
                }
            
            # Esperar antes de reintentar
            time.sleep(1)
            
        finally:
            try:
                if 'cursor' in locals():
                    cursor.close()
                if 'connection' in locals():
                    connection.close()
            except:
                pass

