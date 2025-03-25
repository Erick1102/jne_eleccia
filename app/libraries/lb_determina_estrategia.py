"""Determina la estragia a utilizar dependiendo del tipo de expediente y materia relacionada"""
from app.libraries.core.lb_estragias_ins_list import EstrategiaInscripcionLista


def obtener_estrategia(tipo_materia: int, tipo_expediente: int):
    """Devuelve la estrategia adecuada según el tipo de materia y tipo de expediente."""
    if tipo_expediente == 1:
        if tipo_materia == 1:
            return EstrategiaInscripcionLista()
        elif tipo_materia == 2:            
            raise ValueError("Estrategia para materia 2 no soportada en expediente tipo 1.")
        else:
            raise ValueError("Tipo de materia no soportado para este tipo de expediente.")
    
    elif tipo_expediente == 2:
        if tipo_materia == 1:
            return 1
        elif tipo_materia == 2:
            return 2
        else:
            raise ValueError("Tipo de materia no soportado para este tipo de expediente.")
    
    elif tipo_expediente == 3:
        
        raise NotImplementedError("Estrategia para expediente tipo 3 aún no implementada.")
    
    else:
        raise ValueError("Tipo de expediente no soportado.")
