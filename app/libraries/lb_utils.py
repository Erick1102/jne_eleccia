import os

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
    
    candidatos_path = os.path.join(expediente_path, "resoluciones")
    os.makedirs(candidatos_path, exist_ok=True)

    return expediente_path, documentos_path, candidatos_path

def validar_expediente(num_expediente: str,tipo_expediente: int, tipo_materia: int) -> bool:
    """Valida si el expediente pertenece al tipo de materia especificado."""
    
    return tipo_materia == 1

def define_template(tipo_expediente: int, tipo_materia: int):
    """Define el template html a utilizar."""
    if tipo_materia == 1:
        return "./views/inscripcion_lista.html"
    elif tipo_materia == 2:
        return "./views/apelacion.html"
    else:
        return None
