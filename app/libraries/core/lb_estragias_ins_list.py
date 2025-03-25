"""Conjunto de estrategias para el tipo de expediente inscipción de lista"""

from fastapi import HTTPException
import json
from app.libraries.lb_extrae_info import buscar_documentos, buscar_candidatos, buscar_documentos_candidatos

class EstrategiaExpediente:
    """Clase base para las estrategias de expedientes."""
    def procesar_expediente(self, num_expediente: str) -> dict:
        raise NotImplementedError("La estrategia debe implementar el método procesar_expediente.")

class EstrategiaInscripcionLista(EstrategiaExpediente):
    """Estrategia para el manejo de expedientes de inscripción de lista."""
    def procesar_expediente(self, num_expediente: str) -> dict:
        # Llamamos a las funciones de búsqueda de documentos para inscripción de lista
        documentos = buscar_documentos(num_expediente)
        documentos_candidatos = buscar_documentos_candidatos(num_expediente)
        info_candidatos = buscar_candidatos(num_expediente)
        template = "./views/inscripcion_lista.html"
        try:
            documentos = json.loads(documentos) if isinstance(documentos, str) else documentos
            documentos_candidatos = json.loads(documentos_candidatos) if isinstance(documentos_candidatos, str) else documentos_candidatos
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Error al procesar la respuesta: {str(e)}")

        if "error" in documentos:
            raise HTTPException(status_code=500, detail=documentos["error"])

        if "error" in documentos_candidatos:
            raise HTTPException(status_code=500, detail=documentos_candidatos["error"])

        datos_analisis = {
            "analisis_realizado": True,
            "total_requisitos": 28,
            "requisitos_cumplidos": 21,
            "requisitos_faltantes": 7,
            "porcentaje_cumplimiento": 75,
            "mensaje_alerta": "Faltan requisitos críticos para la inscripción. Se recomienda subsanar las observaciones a la brevedad posible.",
            "tipo_resolucion": "Resolución de Inadmisibilidad",
            "motivo_resolucion": "Incumplimiento de requisitos formales que pueden ser subsanados en un plazo de 2 días hábiles.",
            "tabs": [
                {
                    "id": "solicitud",
                    "nombre": "Solicitud de Inscripción",
                    "requisitos": [
                        {
                            "nombre": "Formulario de solicitud firmado",
                            "descripcion": "El formulario de solicitud de inscripción de lista de candidatos está firmado por todos los candidatos y el personero legal.",
                            "estado": "cumple",
                            "estado_color": "green",
                            "estado_texto": "Cumple",
                            "metodo_validacion": "Verificado con firma digital",
                            "boton_accion": "Ver documento"
                        },
                        {
                            "nombre": "Cuota joven",
                            "descripcion": "La lista de candidatos no cumple con la cuota joven requerida (mínimo 20%).",
                            "estado": "no_cumple",
                            "estado_color": "red",
                            "estado_texto": "No cumple",
                            "observacion": "Se necesita incluir al menos 2 candidatos adicionales entre 18 y 29 años. El análisis detectó que solo el 15% de candidatos cumple con esta cuota, cuando el mínimo requerido es 20% según Ley N° 31030.",
                            "metodo_validacion": "Validado automáticamente",
                            "boton_accion": "Ver detalles"
                        }
                    ]
                },
                {
                    "id": "eleccion",
                    "nombre": "Elección Interna",
                    "requisitos": [
                        {
                            "nombre": "Acta de elección interna - Candidatos",
                            "descripcion": "El acta de elección interna presentada cumple con los candidatos elegidos o designados, y estos corresponden a los presentados en la solicitud.",
                            "estado": "cumple",
                            "estado_color": "green",
                            "estado_texto": "Cumple",
                            "metodo_validacion": "Verificado con SIJE",
                            "boton_accion": "Ver documento"
                        },
                        {
                            "nombre": "Modalidad de elección interna",
                            "descripcion": "El acta de elección interna ha señalado la modalidad empleada, pero se requiere verificación manual del documento.",
                            "estado": "revision",
                            "estado_color": "yellow",
                            "estado_texto": "Requiere revisión",
                            "observacion": "La modalidad señalada no coincide con la permitida en el estatuto de la organización.",
                            "metodo_validacion": "Validación mixta",
                            "boton_accion": "Ver documento"
                        },
                        {
                            "nombre": "Orden de lista",
                            "descripcion": "La lista presentada coincide con el orden de la lista consignada en el acta de elección interna.",
                            "estado": "cumple",
                            "estado_color": "green",
                            "estado_texto": "Cumple",
                            "metodo_validacion": "Verificado automáticamente",
                            "boton_accion": "Ver comparación"
                        }
                    ]
                },
                {
                    "id": "designacion",
                    "nombre": "Designación Directa",
                    "requisitos": []  # Simulado vacío
                },
                {
                    "id": "candidatos",
                    "nombre": "Información de Candidatos",
                    "requisitos": []  # Simulado vacío
                },
                {
                    "id": "plan",
                    "nombre": "Plan de Gobierno y Tasa",
                    "requisitos": []  # Simulado vacío
                }
            ]
        }

        return datos_analisis, template

