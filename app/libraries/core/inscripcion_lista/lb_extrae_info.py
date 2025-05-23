import os
import json
import requests
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from sqlalchemy.sql import func

# Librerias Propias
from app.database.db_scripts import Documentos, Candidatos, Documentos_candidato, Expediente_sije
from app.database.db_session import SessionLocal
from app.config.cf_constantes import BASE_PATH_DOCUMENTOS # Ruta para los documentos
from app.libraries.lb_utils import crear_carpetas
from app.database.models.db_models_eleccia import Expediente, ConfiguracionRequisito, Requisito, Candidato, Estado
from app.libraries.core.inscripcion_lista.lb_req_sol_ins import verificar_comunidad_campesina

def buscar_documentos(num_expediente):
    """Consulta los documentos de un expediente y los descarga en una carpeta específica."""
    # Crear una sesión de base de datos
    db = SessionLocal()
    
    try:
        # Ejecutar la consulta
        resultados = db.execute(Documentos, {"TXCODEXPEDIENTEEXT": num_expediente}).fetchall()
        
        if not resultados:
            return {"mensaje": "No se encontraron documentos para el expediente."}

        # Crear carpetas usando la función crear_carpetas
        _, documentos_path, _ = crear_carpetas(num_expediente, BASE_PATH_DOCUMENTOS)

        documentos = []
        urls_documentos = {}
        
        for doc in resultados:
            tipo_documento = doc[3]  # Tipo de documento
            if tipo_documento == 13:
                tx_descripcion = "SOLICITUD_DE_INSCRIPCION"
            elif tipo_documento == 8:
                tx_descripcion = "PLAN_DE_GOBIERNO"
            elif tipo_documento == 3:
                tx_descripcion = "ACTA_DE_ELECCION_INTERNA"
            elif tipo_documento == 7:
                tx_descripcion = "RESUMEN_PLAN_GOBIERNO"
            else:
                tx_descripcion = doc[4].replace(" ", "_")  # Nombres de los documentos por defecto
            
            url_documento = doc[7]  # Ruta de descarga
            archivo_nombre = f"{tx_descripcion}.pdf"  # Ruta local
            
            archivo_local = os.path.join(documentos_path, archivo_nombre)  # Ruta donde se guardará el archivo

            # Descargar archivo
            try:
                response = requests.get(url_documento, stream=True)
                if response.status_code == 200:
                    with open(archivo_local, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    documentos.append(archivo_nombre)
                    # Guardar la URL asociada al tipo de documento
                    urls_documentos[tx_descripcion] = {
                        "url": url_documento,
                        "tipo_documento": tipo_documento
                    }

            except Exception as e:
                print(f"Error al descargar el documento {tx_descripcion}: {str(e)}")
        
        return {
            "EXPEDIENTE": num_expediente, 
            "DOCUMENTOS": documentos,
            "URLS_DOCUMENTOS": urls_documentos
        }
    
    except Exception as e:
        print(f"Error en buscar_documentos: {str(e)}")
        return {"error": str(e)}

    finally:
        db.close()

def buscar_candidatos(num_expediente):
    """Consulta los datos de los candidatos pertenecientes a la solicitud de lista."""
    # Crear una sesión de base de datos
    db = SessionLocal()

    try:
        # Ejecutar la consulta
        resultados = db.execute(Candidatos, {"TXCODEXPEDIENTEEXT": num_expediente}).fetchall()

        if not resultados:
            return {"mensaje": "No se encontraron candidatos para la lista."}

        # Crear el diccionario para agrupar a los candidatos por DNI
        candidatos_agrupados = {}

        for candidato in resultados:            
            dni = candidato[3]  # TXDOCUMENTOIDENTIDAD
            tx_nombres = candidato[6]  # TXNOMBRES
            tx_apellidos = candidato[4] + " " + candidato[5]  # TXAPELLIDOPATERNO + TXAPELLIDOMATERNO
            tx_sexo = "Hombre" if candidato[7] == "1" else "Mujer"  # TXSEXO
            tx_fecha_nac = candidato[8]  # FENACIMIENTO
            tx_edad = candidato[9]  # NUEDAD
            tx_ubigeo_domicilio = candidato[10] #TXDOMICILIODIRECC
            tx_direc_region = candidato[11]  # TXDIRECCIONREGION
            tx_domicilio = candidato[12] #TXDOMICILIODIRECC
            tx_cargo_eleccion = candidato[13]  # TXCARGOELECCION
            tx_ubigeo_region = candidato[14]  # TXUBIGOPostULAREGION
            tx_postula_region = candidato[15]  # TXPOSTULAREGION
            tx_nuposicion = candidato[17]  # NUPOSICION
            tx_nativo = candidato[18]  # FGNATIVO
            tx_pais_nacimiento = candidato[19]  # TXPAISNACIMIENTO
            tx_organizacion_politica = candidato[20]  # TXORGANIZACIONPOLITICA
            tx_nregidores = candidato[21] #NUREGIDORES
            # Agrupar los candidatos por DNI
            if dni not in candidatos_agrupados:
                candidatos_agrupados[dni] = []

            candidatos_agrupados[dni].append({
                "tx_dni": dni,
                "tx_nombres": tx_nombres,
                "tx_apellidos": tx_apellidos,
                "tx_sexo": tx_sexo,
                "tx_fecha_nac": tx_fecha_nac,
                "tx_edad": tx_edad,
                "tx_pais_nacimiento": tx_pais_nacimiento,
                "tx_ubigeo": tx_ubigeo_domicilio,
                "tx_direc_region": tx_direc_region,
                "tx_domicilio": tx_domicilio,
                "tx_cargo_eleccion": tx_cargo_eleccion,
                "tx_ubigeo_postula": tx_ubigeo_region,
                "tx_postula_region": tx_postula_region,
                "tx_nuposicion": tx_nuposicion,
                "tx_nativo": tx_nativo,
                "tx_organizacion_politica": tx_organizacion_politica,
                "tx_nregidores": tx_nregidores
            })

        # Crear el diccionario final con la estructura esperada
        resultado = {"EXPEDIENTE": num_expediente, "CANDIDATOS": candidatos_agrupados}

        # Guardar los candidatos en la base de datos ELECCIA
        from app.libraries.lb_utils import guardar_candidatos_eleccia
        resultado_guardado = guardar_candidatos_eleccia(db, resultado)

        # Si hubo errores al guardar, agregarlos al resultado
        if "error" in resultado_guardado:
            resultado["error_guardado"] = resultado_guardado["error"]
        elif "errores" in resultado_guardado and resultado_guardado["errores"]:
            resultado["errores_guardado"] = resultado_guardado["errores"]

        return resultado

    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()

def buscar_documentos_candidatos(num_expediente):
    """Consulta los documentos adjuntos para cada candidato y los almacena en la carpeta de documentos del candidato."""
    # Crear una sesión de base de datos
    db = SessionLocal()

    try:
        # Ejecutar la consulta
        resultados = db.execute(Documentos_candidato, {"TXCODEXPEDIENTEEXT": num_expediente}).fetchall()

        if not resultados:
            return {"mensaje": "No se encontraron documentos para el expediente."}

        # Crear las carpetas necesarias
        _, _, candidatos_path = crear_carpetas(num_expediente, BASE_PATH_DOCUMENTOS)

        documentos_candidatos = {}

        for doc in resultados:
            # Extraemos la información relevante de cada documento
            dni = doc[3]  # TXDOCUMENTOIDENTIDAD
            nombre_documento = doc[5].strip()  # TXNOMBRE
            url_documento = doc[7]  # TXRUTAVIRTUAL
            fecha_firma = doc[10]  # FEFIRMADO

            # Creamos la ruta para guardar el archivo del candidato (usando su DNI)
            candidato_path = os.path.join(candidatos_path, str(dni))
            os.makedirs(candidato_path, exist_ok=True)

            # Clean and format document name - replace all whitespace with underscore
            nombre_archivo = '_'.join(nombre_documento.strip().split()) + ".pdf"

            # Ruta completa donde se guardará el archivo descargado
            archivo_local = os.path.join(candidato_path, nombre_archivo)

            # Descargar archivo
            try:                
                response = requests.get(url_documento, stream=True)
                if response.status_code == 200:
                    with open(archivo_local, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    # Añadir el nombre del archivo y su URL al diccionario de documentos del candidato
                    if dni in documentos_candidatos:
                        documentos_candidatos[dni].append({
                            "nombre": nombre_archivo,
                            "url": url_documento,
                            "fecha_firma": fecha_firma
                        })
                    else:
                        documentos_candidatos[dni] = [{
                            "nombre": nombre_archivo,
                            "url": url_documento,
                            "fecha_firma": fecha_firma
                        }]
                else:
                    print(f"Error al descargar el archivo {nombre_archivo} desde {url_documento}. Código {response.status_code}")
            except Exception as e:
                print(f"Hubo un error al descargar el archivo {nombre_archivo}: {e}")

        return {"EXPEDIENTE": num_expediente, "DOCUMENTOS_CANDIDATOS": documentos_candidatos}

    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()

def buscar_personero(num_expediente):

    return 0

def buscar_expediente_sije(num_expediente):
    """Busca el expediente en la base de datos SIJE."""
    # Crear una sesión de base de datos
    db = SessionLocal()

    try:
        # Ejecutar la consulta
        resultados = db.execute(Expediente_sije, {"TXCODEXPEDIENTEEXT": num_expediente}).fetchall()

        if not resultados:
            return {"mensaje": "No se encontraron datos para el expediente."}

        return {"EXPEDIENTE": num_expediente, "DATOS": resultados}
        
    except Exception as e:
        return {"error": str(e)}

    finally:
        db.close()  

def buscar_requisitos_expediente(num_expediente: str, db: Session) -> tuple[list, list]:
    """
    Busca los requisitos del expediente diferenciando entre prioridad 1,2,4 (lista) y prioridad 3 (candidatos).
    Retorna una tupla con: (requisitos_lista, requisitos_candidatos, info_validacion_cc)
    """
    # Obtener el expediente
    expediente = db.query(Expediente).filter(Expediente.nombre_expediente == num_expediente).first()
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    print(f"Expediente encontrado: {expediente.nombre_expediente}, Tipo: {expediente.id_tipo_expediente}, Materia: {expediente.id_materia}")
    
    # Verificar si hay configuraciones para este tipo de expediente y materia
    count = db.query(ConfiguracionRequisito).filter(
        ConfiguracionRequisito.id_tipo_expediente == expediente.id_tipo_expediente,
        ConfiguracionRequisito.id_materia == expediente.id_materia
    ).count()
    
    print(f"Total de configuraciones encontradas: {count}")
    
    
    configuraciones = db.query(ConfiguracionRequisito).options(
        joinedload(ConfiguracionRequisito.requisito)
    ).filter(
        ConfiguracionRequisito.id_tipo_expediente == expediente.id_tipo_expediente,
        ConfiguracionRequisito.id_materia == expediente.id_materia,
        ConfiguracionRequisito.es_obligatorio == 1
    ).all()

    # Si no hay configuraciones, intentar obtener todos los requisitos para depuración
    if not configuraciones:
        print("No se encontraron configuraciones específicas. Mostrando todas las configuraciones disponibles:")
        all_configs = db.query(ConfiguracionRequisito).all()
        print(f"Total de configuraciones en la base de datos: {len(all_configs)}")
        for cfg in all_configs[:5]:  # Mostrar solo los primeros 5 para no saturar la consola
            print(f"Config ID: {cfg.id_configuracion}, Tipo Exp: {cfg.id_tipo_expediente}, Materia: {cfg.id_materia}")
    
    # Separar requisitos por prioridad
    requisitos_lista = []
    requisitos_candidatos = []

    # Obtener información de candidatos para verificar comunidad campesina
    candidatos_info = None
    primer_candidato = None
    ubigeo = None
    info_validacion_cc = {
        'aplica': False,
        'cumple': None,
        'mensaje': "No se pudo determinar si aplica el requisito de comunidad campesina."
    }
    
    try:
        candidatos_info = buscar_candidatos(num_expediente)
        if isinstance(candidatos_info, str):
            candidatos_info = json.loads(candidatos_info)
            
        if (candidatos_info and isinstance(candidatos_info, dict) and 
            'CANDIDATOS' in candidatos_info and 
            candidatos_info.get('mensaje') != "No se encontraron candidatos para la lista."):
            
            primer_candidato = next(iter(candidatos_info['CANDIDATOS'].values()))[0]
            ubigeo = primer_candidato.get('tx_ubigeo_region', '')
            
            # Verificar si aplica el requisito de comunidad campesina
            id_expediente = expediente.id_expediente
            info_validacion_cc = verificar_comunidad_campesina(
                id_expediente, 
                ubigeo, 
                candidatos_info['CANDIDATOS']
            )
    except Exception as e:
        print(f"Error al obtener información de candidatos: {str(e)}")

    # Procesar cada configuración
    for config in configuraciones:
        # Verificar si la relación requisito está cargada correctamente
        if not hasattr(config, 'requisito') or config.requisito is None:
            print(f"Advertencia: Configuración {config.id_configuracion} no tiene requisito asociado")
            # Intentar cargar el requisito manualmente
            requisito = db.query(Requisito).filter(Requisito.id_requisito == config.id_requisito).first()
            if not requisito:
                print(f"No se pudo encontrar el requisito con ID {config.id_requisito}")
                continue
        else:
            requisito = config.requisito
        
        print(f"Procesando requisito: {requisito.codigo_requisito}, Prioridad: {config.prioridad}")
        
        # Construir el diccionario de requisito con todos los campos necesarios
        req_dict = {
            'id_configuracion': config.id_configuracion,
            'nombre_requisito': requisito.nombre_requisito,
            'codigo': requisito.codigo_requisito,
            'descripcion': requisito.descripcion,
            'es_obligatorio': config.es_obligatorio,
            'prioridad': config.prioridad
        }
        
        # Caso especial para CUOTA_COMUNIDAD_CAMPESINA
        if requisito.codigo_requisito == 'CUOTA_COMUNIDAD_CAMPESINA':
            # Solo agregar si aplica según la validación previa
            if info_validacion_cc is not None and info_validacion_cc.get('aplica', False):
                if config.prioridad == 1:
                    requisitos_lista.append(req_dict)
                else:
                    requisitos_candidatos.append(req_dict)
        else:
            # Para todos los demás requisitos, agregarlos según su prioridad
            if config.prioridad in [1, 2, 4]:
                requisitos_lista.append(req_dict)
            else:
                requisitos_candidatos.append(req_dict)
    
    return requisitos_lista, requisitos_candidatos, info_validacion_cc

