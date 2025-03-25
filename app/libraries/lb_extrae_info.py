import os
import requests

# Librerias Propias
from app.database.db_scripts import Documentos, Candidatos, Documentos_candidato
from app.database.db_session import SessionLocal
from app.config.cf_constantes import BASE_PATH_DOCUMENTOS # Ruta para los documentos

def crear_carpetas(num_expediente, BASE_PATH_DOCUMENTOS):
    """
    Crea la estructura de carpetas necesaria para almacenar los documentos del expediente.
    
    :param num_expediente: El número del expediente.
    :param base_path_documentos: Ruta base donde se almacenarán los documentos.
    :return: Ruta de las carpetas creadas.
    """
    # carpeta principal del expediente
    expediente_path = os.path.join(BASE_PATH_DOCUMENTOS, str(num_expediente))
    os.makedirs(expediente_path, exist_ok=True)

    # subcarpetas para documentos de expediente y documentos de candidatos
    documentos_path = os.path.join(expediente_path, "documentos_expediente")
    os.makedirs(documentos_path, exist_ok=True)
    
    candidatos_path = os.path.join(expediente_path, "documentos_candidato")
    os.makedirs(candidatos_path, exist_ok=True)

    candidatos_path = os.path.join(expediente_path, "resoluciones")
    os.makedirs(candidatos_path, exist_ok=True)
    
    return expediente_path, documentos_path, candidatos_path

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
        expediente_path, documentos_path, candidatos_path = crear_carpetas(num_expediente, BASE_PATH_DOCUMENTOS)

        documentos = []
        
        for doc in resultados:
            tx_descripcion = doc[4].replace(" ", "_")  # Nombres de los documentos
            url_documento = doc[7]  # Ruta de descarga
            archivo_nombre = f"{tx_descripcion}.pdf"  # Ruta local
            
            archivo_local = os.path.join(documentos_path, archivo_nombre)  # Ruta donde se guardará el archivo

            # Descargar archivo
            response = requests.get(url_documento, stream=True)
            if response.status_code == 200:
                with open(archivo_local, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                documentos.append(archivo_nombre)
            else:
                print(f"Error al descargar {url_documento}: Código {response.status_code}")
        
        return {"EXPEDIENTE": num_expediente, "DOCUMENTOS": documentos}
    
    except Exception as e:
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
            # Obtener el DNI del candidato (posiblemente la columna 3 en la base de datos)
            dni = candidato[3]  # TXDOCUMENTOIDENTIDAD
            tx_nombres = candidato[6]  # TXNOMBRES
            tx_apellidos = candidato[4] + " " + candidato[5]  # TXAPELLIDOPATERNO + TXAPELLIDOMATERNO
            tx_sexo = "Hombre" if candidato[8] == 1 else "Mujer"  # TXSEXO
            tx_fecha_nac = candidato[9]  # FENACIMIENTO
            tx_edad = candidato[13]  # NUEDAD
            tx_direccion = candidato[10]  # TXDIRECCION
            tx_cargo_eleccion = candidato[14]  # TXCARGOELECCION
            tx_postula_region = candidato[13]  # TXPOSTULAREGION
            tx_nuposicion = candidato[15]  # NUPOSICION

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
                "tx_direccion": tx_direccion,
                "tx_cargo_eleccion": tx_cargo_eleccion,
                "tx_postula_region": tx_postula_region,
                "tx_nuposicion": tx_nuposicion,
            })

        return {"EXPEDIENTE": num_expediente, "CANDIDATOS": candidatos_agrupados}

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
        expediente_path, documentos_path, candidatos_path = crear_carpetas(num_expediente, BASE_PATH_DOCUMENTOS)

        documentos_candidatos = {}

        for doc in resultados:
            # Extraemos la información relevante de cada documento
            dni = doc[3]  # TXDOCUMENTOIDENTIDAD
            nombre_documento = doc[5]  # TXNOMBRE
            url_documento = doc[6]  # TXRUTAVIRTUAL

            # Creamos la ruta para guardar el archivo del candidato (usando su DNI)
            candidato_path = os.path.join(candidatos_path, str(dni))
            os.makedirs(candidato_path, exist_ok=True)

            nombre_archivo = nombre_documento.replace(" ", "_") + ".pdf"

            # Ruta completa donde se guardará el archivo descargado
            archivo_local = os.path.join(candidato_path, nombre_archivo)

            # Descargar archivo
            try:                
                response = requests.get(url_documento, stream=True)
                if response.status_code == 200:
                    with open(archivo_local, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    # Añadir el nombre del archivo al diccionario de documentos del candidato
                    if dni in documentos_candidatos:
                        documentos_candidatos[dni].append(nombre_archivo)
                    else:
                        documentos_candidatos[dni] = [nombre_archivo]
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