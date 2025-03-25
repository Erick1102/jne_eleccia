from fastapi import HTTPException
import json

from app.libraries.lb_extrae_info import buscar_documentos, buscar_candidatos, buscar_documentos_candidatos # Extrae documentos


class EstrategiaExpediente:
    """Clase base para las estrategias de expedientes."""
    def procesar_expediente(self, num_expediente: str) -> dict:
        raise NotImplementedError("La estrategia debe implementar el método procesar_expediente.")


class EstrategiaInscripcionLista(EstrategiaExpediente):
    """Estrategia para el manejo de expedientes de inscripción de lista."""
    def procesar_expediente(self, num_expediente: str) -> dict:

        # Llamamos a las funciones de búsqueda de documentos para inscripcion de lista
        documentos = buscar_documentos(num_expediente) # Busqueda de documentos del expediente
        documentos_candidatos = buscar_documentos_candidatos(num_expediente) # Busqueda de docuementos de los candidatos
        info_candidatos = buscar_candidatos(num_expediente) # Buscar informacion de los candidatos
        
        #datos_analizados = estructura_datos_analizados(documentos, documentos_candidatos,info_candidatos,materia=1)

        # Convertimos las respuestas JSON a diccionarios
        try:
            documentos = json.loads(documentos) if isinstance(documentos, str) else documentos
            documentos_candidatos = json.loads(documentos_candidatos) if isinstance(documentos_candidatos, str) else documentos_candidatos
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Error al procesar la respuesta: {str(e)}")

        if "error" in documentos:
            raise HTTPException(status_code=500, detail=documentos["error"])

        if "error" in documentos_candidatos:
            raise HTTPException(status_code=500, detail=documentos_candidatos["error"])
        
        return {
            "documentos": documentos,
            "info_candidatos": info_candidatos,
            "documentos_candidatos": documentos_candidatos
        }


def obtener_estrategia(tipo_materia: int, tipo_expediente: int) -> EstrategiaExpediente:
    """Devuelve la estrategia adecuada según el tipo de materia y tipo de expediente."""
    if tipo_expediente == 1:
        if tipo_materia == 1:
            return EstrategiaInscripcionLista()
        else:
            raise ValueError("Tipo de materia no soportado para este tipo de expediente.")
    
    elif tipo_expediente == 2:
        if tipo_materia == 1:
            return "estrategia2"
        else:
            raise ValueError("Tipo de materia no soportado para este tipo de expediente.")
    
    else:
        raise ValueError("Tipo de expediente no soportado.")