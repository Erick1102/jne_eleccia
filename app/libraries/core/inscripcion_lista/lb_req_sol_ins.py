"""
Validación de los requisitos de la solicitud de inscripción.
"""
from app.database.db_session import get_db
from app.libraries.lb_utils import obtener_id_expediente_eleccia, actualizar_estado_requisito, verificar_estado_requisito
from app.services.sr_ia_services import validar_firma_digital
from app.database.models.db_models_eleccia import EstadoRequisitoExpediente, ConfiguracionRequisito, Requisito

#db = SessionLocal()
usuario = 'ELECCIA'

def verificar_comunidad_campesina(db,id_expediente: int, ubigeo: str, candidatos: dict = None, archivo_ruta: str = None) -> dict:
    """
    Verifica si un ubigeo pertenece a una zona de comunidad campesina y si aplica la cuota.
    
    Args:
        id_expediente: ID del expediente
        ubigeo: Código de ubigeo
        candidatos: Diccionario con información de candidatos
        archivo_ruta: Ruta del archivo asociado
        
    Returns:
        Diccionario con información sobre si aplica, si cumple, y mensaje
    """
    # Verificar si pertenece a zona de comunidad campesina
    zonas_comunidad_campesina = ['010101']  # Código de ubigeo para Chachapoyas
    es_zona_cc = ubigeo in zonas_comunidad_campesina
    
    # Si no es zona de comunidad campesina, no aplica el requisito
    if not es_zona_cc:
        return {
            'aplica': False,
            'cumple': None,  # None indica que no aplica
            'mensaje': "La lista no pertenece a una zona de comunidad campesina (No aplica)."
        }
    
    # Si no hay información de candidatos, consideramos que aplica pero no podemos evaluar
    if not candidatos:
        return {
            'aplica': True,
            'cumple': False,
            'mensaje': "No se puede validar: Falta información de candidatos."
        }
    
    # Contar candidatos totales y nativos
    total_candidatos = 0
    total_nativos = 0
    
    for candidatos_dni in candidatos.values():
        for candidato in candidatos_dni:
            total_candidatos += 1
            if candidato.get('tx_nativo', '') == 'SI':
                total_nativos += 1
    
    # Verificar si cumple la cuota del 15%
    if total_candidatos == 0:
        cumple = False
        mensaje = "No hay candidatos en la lista"
    else:
        porcentaje_nativos = (total_nativos / total_candidatos) * 100
        cumple = porcentaje_nativos >= 15
        mensaje = f"La lista tiene {porcentaje_nativos:.1f}% de candidatos de comunidad campesina ({total_nativos} de {total_candidatos})"
        
        if not cumple:
            mensaje += ". Se requiere mínimo 15% de candidatos de comunidad campesina."
    
    return {
        'aplica': True,
        'cumple': cumple,
        'mensaje': mensaje
    }

def validar_cuota_genero(db,id_expediente: int, datos_candidatos: dict, archivo_ruta: str = None) -> tuple[bool, str]:
    """
    Valida que el cuerpo de la lista cumpla con la cuota de género (50% de cada género).
    Siempre excluye al alcalde (primer candidato) y aplica regla especial según si el cuerpo de la lista es par o impar.
    Retorna una tupla con (cumple, mensaje)
    """
    
    candidatos = datos_candidatos.get("CANDIDATOS", {})
    
    total_candidatos = 0
    total_mujeres = 0
    total_hombres = 0
    
    # Contar candidatos del cuerpo de la lista (excluyendo al alcalde)
    for dni, candidatos_dni in candidatos.items():
        for candidato in candidatos_dni:
            # Excluir al alcalde (posición 0)
            if int(candidato.get('tx_nuposicion', 0)) == 0:
                continue
                
            total_candidatos += 1
            sexo = candidato.get('tx_sexo', '').strip()
            if sexo == 'Mujer':
                total_mujeres += 1
            else:
                total_hombres += 1
    
    if total_candidatos == 0:
        return False, "No hay candidatos en el cuerpo de la lista"
    
    # Calcular porcentajes
    porcentaje_mujeres = (total_mujeres / total_candidatos) * 100
    porcentaje_hombres = (total_hombres / total_candidatos) * 100
    
    # Determinar si el cuerpo de la lista es par o impar
    es_cuerpo_impar = total_candidatos % 2 != 0
    
    # Aplicar reglas según paridad del cuerpo de la lista
    if es_cuerpo_impar:
        # Para cuerpos impares, se permite un 50% de tolerancia
        cumple = porcentaje_mujeres >= 25 and porcentaje_hombres >= 25
    else:
        # Para cuerpos pares, se requiere exactamente 50% de cada género
        cumple = porcentaje_mujeres == 50 and porcentaje_hombres == 50
    
    mensaje = f"El cuerpo de la lista tiene {porcentaje_mujeres:.1f}% de mujeres ({total_mujeres} candidatas) y {porcentaje_hombres:.1f}% de hombres ({total_hombres} candidatos)"
    
    if not cumple:
        if es_cuerpo_impar:
            mensaje += ". Para cuerpos de lista impares se requiere mínimo 25% de cada género."
        else:
            mensaje += ". Para cuerpos de lista pares se requiere exactamente 50% de cada género."
    
    return cumple, mensaje

def validar_cuota_joven(db,id_expediente: int, datos_candidatos: dict, archivo_ruta: str = None) -> tuple[bool, str]:
    """
    Valida que la lista cumpla con la cuota joven (mínimo 20% de candidatos entre 18 y 29 años).
    Retorna una tupla con (cumple, mensaje)
    """
    candidatos = datos_candidatos.get("CANDIDATOS", {})
    total_candidatos = 0
    total_jovenes = 0
    
    for candidatos_dni in candidatos.values():
        for candidato in candidatos_dni:
            if int(candidato.get('tx_nuposicion', 0)) == 0:
                continue
            
            total_candidatos += 1
            edad = int(candidato['tx_edad'])
            if 18 <= edad <= 29:
                total_jovenes += 1
    
    if total_candidatos == 0:
        return False, "No hay candidatos en la lista"
    
    porcentaje_jovenes = (total_jovenes / total_candidatos) * 100
    cumple = porcentaje_jovenes >= 20
    mensaje = f"La lista tiene {porcentaje_jovenes:.1f}% de jóvenes ({total_jovenes} de {total_candidatos} candidatos)"
    
    if not cumple:
        mensaje += ". Se requiere mínimo 20% de jóvenes (18-29 años)."
    
    return cumple, mensaje

def validar_paridad(db, id_expediente: int, datos_candidatos: dict, archivo_ruta: str = None) -> tuple[bool, str]:
    """
    Valida que la lista cumpla con la paridad (intercalado hombre/mujer).
    Excluye al candidato en la posición 0 (primer candidato de la lista).
    Retorna una tupla con (cumple, mensaje)
    """
    candidatos = datos_candidatos.get("CANDIDATOS", {})
    # Ordenar candidatos por posición
    candidatos_ordenados = []
    for candidatos_dni in candidatos.values():
        for candidato in candidatos_dni:
            candidatos_ordenados.append(candidato)
    
    candidatos_ordenados.sort(key=lambda x: int(x['tx_nuposicion']))
    
    # Filtrar candidatos excluyendo la posición 0
    candidatos_para_validar = [c for c in candidatos_ordenados if int(c['tx_nuposicion']) > 0]
    
    if len(candidatos_para_validar) < 2:
        cumple = True
        mensaje = "La lista tiene menos de 2 candidatos (excluyendo al primero), no aplica paridad"
    else:
        # Verificar intercalado
        cumple = True
        mensaje = "La lista cumple con la paridad (intercalado hombre/mujer, aplicado al cuerpo de la lista)"
        
        for i in range(1, len(candidatos_para_validar)):
            sexo_actual = candidatos_para_validar[i]['tx_sexo']
            sexo_anterior = candidatos_para_validar[i-1]['tx_sexo']
            
            if sexo_actual == sexo_anterior:
                cumple = False
                posicion_actual = int(candidatos_para_validar[i]['tx_nuposicion'])
                posicion_anterior = int(candidatos_para_validar[i-1]['tx_nuposicion'])
                mensaje = f"La lista no cumple con la paridad. Los candidatos en posiciones {posicion_anterior} y {posicion_actual} son del mismo sexo"
                break
    
    return cumple, mensaje

def validar_firma_solicitud_inscripcion(db, id_expediente: int, num_expediente: str, archivo_ruta: str = None) -> tuple[bool, str]:
    """
    Valida que la solicitud de inscripción esté firmada.
    Retorna una tupla con (cumple, mensaje)
    """
    try:        
        # Validar firma usando el servicio de IA
        cumple_firma, mensaje_firma = validar_firma_digital("SOLICITUD_DE_INSCRIPCION.pdf", num_expediente)
        return cumple_firma, mensaje_firma
        
    except Exception as e:
        mensaje = "ELECCIA no pudo verificar este requisito, validar"
        return None, mensaje

def validar_cantidad_regidores(db, id_expediente: int, datos_candidatos: dict, archivo_ruta: str = None) -> tuple[bool, str]:
    """
    Valida que la cantidad de regidores en la lista coincida con el número requerido según el ubigeo.
    Excluye al alcalde (posición 0) del conteo.
    Retorna una tupla con (cumple, mensaje)
    """
    candidatos = datos_candidatos.get("CANDIDATOS", {})
    
    # Obtener el número de regidores requerido del primer candidato
    primer_candidato = next(iter(candidatos.values()))[0]
    regidores_requeridos = int(primer_candidato.get('tx_nregidores', 0))
    lugar_electoral = primer_candidato.get('tx_postula_region', '').split('/')[-1]
    
    # Contar regidores (excluyendo al alcalde)
    total_regidores = 0
    for candidatos_dni in candidatos.values():
        for candidato in candidatos_dni:
            # Excluir al alcalde (posición 0)
            if int(candidato.get('tx_nuposicion', 0)) == 0:
                continue
            total_regidores += 1
    
    # Verificar si coincide con el número requerido
    cumple = total_regidores == regidores_requeridos
    mensaje = f"La lista tiene {total_regidores} regidores para {lugar_electoral}"
    
    if not cumple:
        mensaje += f". Se requieren {regidores_requeridos} regidores para este distrito."
    else:
        mensaje += ". Cumple con la cantidad de regidores requerida."
    
    return cumple, mensaje

def validar_requisitos_lista(num_expediente:str, datos_candidatos: dict, ubigeo: str, info_validacion_cc: dict = None, urls_documentos: dict = None) -> dict:
    """
    Valida todos los requisitos de la lista.
    Retorna un diccionario con los resultados de cada validación.
    
    Args:
        num_expediente: Número de expediente
        datos_candidatos: Diccionario con información de candidatos
        ubigeo: Código de ubigeo
        info_validacion_cc: Información de validación de comunidad campesina
        urls_documentos: Diccionario con URLs de documentos del expediente
    """
    from concurrent.futures import ThreadPoolExecutor
    import concurrent.futures

    resultados = {}
    db = next(get_db())
    # Obtener ID de expediente de elección
    id_expediente_eleccia = obtener_id_expediente_eleccia(db, num_expediente)
    if not id_expediente_eleccia:
        return {"error": "No se encontró el expediente"}
    
    # Obtener URL de solicitud de inscripción
    url_solicitud = None
    if urls_documentos and 'SOLICITUD_DE_INSCRIPCION' in urls_documentos:
        url_solicitud = urls_documentos['SOLICITUD_DE_INSCRIPCION']['url']

    # Crear funciones auxiliares para cada validación sin actualizar la base de datos
    def ejecutar_validacion_genero():
        cumple, mensaje = validar_cuota_genero(db, id_expediente_eleccia, {"CANDIDATOS": datos_candidatos}, None)
        return 'CUOTA_GENERO', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_solicitud
        }

    def ejecutar_validacion_joven():
        cumple, mensaje = validar_cuota_joven(db, id_expediente_eleccia, {"CANDIDATOS": datos_candidatos}, None)
        return 'CUOTA_JOVEN', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_solicitud
        }

    def ejecutar_validacion_cc():
        if info_validacion_cc is None:
            info = verificar_comunidad_campesina(db, id_expediente_eleccia, ubigeo, datos_candidatos, None)
        else:
            info = info_validacion_cc
            
        # Solo incluir en resultados si aplica
        if info.get('aplica', False) and info.get('cumple') is not None:
            return 'CUOTA_COMUNIDAD_CAMPESINA', {
                'cumple': info['cumple'],
                'mensaje': info['mensaje'],
                'url_documento': url_solicitud
            }
        return None, None

    def ejecutar_validacion_paridad():
        cumple, mensaje = validar_paridad(db, id_expediente_eleccia, {"CANDIDATOS": datos_candidatos}, None)
        return 'PARIDAD', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_solicitud
        }

    def ejecutar_validacion_regidores():
        cumple, mensaje = validar_cantidad_regidores(db, id_expediente_eleccia, {"CANDIDATOS": datos_candidatos}, None)
        return 'CANTIDAD_REGIDORES', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_solicitud
        }

    def ejecutar_validacion_firma():
        cumple, mensaje = validar_firma_solicitud_inscripcion(db, id_expediente_eleccia, num_expediente, None)
        return 'SOLICITUD_INSCRIPCION_FIRMADA', {
            'cumple': cumple,
            'mensaje': mensaje,
            'url_documento': url_solicitud
        }

    # Ejecutar todas las validaciones en paralelo
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_validacion = {
            executor.submit(ejecutar_validacion_genero): 'CUOTA_GENERO',
            executor.submit(ejecutar_validacion_joven): 'CUOTA_JOVEN',
            executor.submit(ejecutar_validacion_cc): 'CUOTA_COMUNIDAD_CAMPESINA',
            executor.submit(ejecutar_validacion_paridad): 'PARIDAD',
            executor.submit(ejecutar_validacion_regidores): 'CANTIDAD_REGIDORES',
            executor.submit(ejecutar_validacion_firma): 'SOLICITUD_INSCRIPCION_FIRMADA'
        }

        # Recopilar resultados cuando estén disponibles
        for future in concurrent.futures.as_completed(future_to_validacion):
            try:
                codigo, resultado = future.result()
                if codigo is not None and resultado is not None:  # Solo incluir si no es None
                    resultados[codigo] = resultado
            except Exception as e:
                codigo = future_to_validacion[future]
                resultados[codigo] = {
                    'cumple': False,
                    'mensaje': f"Error en la validación: {str(e)}",
                    'url_documento': url_solicitud
                }
    
    return resultados

