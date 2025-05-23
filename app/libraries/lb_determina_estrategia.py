"""Determina la estrategia a utilizar dependiendo del tipo de expediente y materia relacionada"""
from app.libraries.core.inscripcion_lista.lb_estrategias_ins_list import EstrategiaInscripcionLista

def obtener_estrategia(tipo_materia: int, tipo_expediente: int):
    """Devuelve la estrategia adecuada según el tipo de materia y tipo de expediente."""
    
    # Diccionario de estrategias por tipo de expediente y materia
    estrategias = {
        5: {  # Tipo de expediente 5 - Inscripción de Lista
            1: EstrategiaInscripcionLista(),  # Solicitud Inscripción de Lista
            2: lambda: _lanzar_error("Estrategia para materia 2 no implementada en Inscripción de Lista."),
            3: lambda: _lanzar_error("Estrategia para materia 3 no implementada en Inscripción de Lista."),
            4: lambda: _lanzar_error("Estrategia para materia 4 no implementada en Inscripción de Lista."),
            5: lambda: _lanzar_error("Estrategia para materia 5 no implementada en Inscripción de Lista."),
            6: lambda: _lanzar_error("Estrategia para materia 6 no implementada en Inscripción de Lista."),
            7: lambda: _lanzar_error("Estrategia para materia 7 no implementada en Inscripción de Lista."),
            8: lambda: _lanzar_error("Estrategia para materia 8 no implementada en Inscripción de Lista."),
            9: lambda: _lanzar_error("Estrategia para materia 9 no implementada en Inscripción de Lista."),
            "default": lambda: _lanzar_error("Tipo de materia no soportado para Inscripción de Lista.")
        },
        2: {  # Tipo de expediente 2
            "default": lambda: _lanzar_error("Estrategia para expediente tipo 2 aún no implementada.")
        },
        3: {  # Tipo de expediente 3
            "default": lambda: _lanzar_error("Estrategia para expediente tipo 3 aún no implementada.")
        },
        4: {  # Tipo de expediente 4
            "default": lambda: _lanzar_error("Estrategia para expediente tipo 4 aún no implementada.")
        },
        1: {  # Tipo de expediente 1
            "default": lambda: _lanzar_error("Estrategia para expediente tipo 1 aún no implementada.")
        },
        "default": lambda: _lanzar_error("Tipo de expediente no soportado.")
    }

    # Función auxiliar para lanzar errores
    def _lanzar_error(mensaje: str):
        raise ValueError(mensaje)

    # Obtener la estrategia del diccionario
    estrategia_expediente = estrategias.get(tipo_expediente, estrategias["default"])
    if callable(estrategia_expediente):
        return estrategia_expediente()
    
    estrategia_materia = estrategia_expediente.get(tipo_materia, estrategia_expediente["default"])
    if callable(estrategia_materia):
        return estrategia_materia()
    
    return estrategia_materia
