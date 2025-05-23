"""Conjunto de estrategias para el tipo de expediente inscipción de lista"""

import json
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

from app.database.db_session import SessionLocal
from app.libraries.core.inscripcion_lista.lb_extrae_info import buscar_documentos, buscar_candidatos, buscar_documentos_candidatos
from app.libraries.core.inscripcion_lista.lb_req_sol_ins import validar_requisitos_lista
from app.libraries.core.inscripcion_lista.lb_req_acta_interna import validar_requisitos_acta_interna
from app.libraries.core.inscripcion_lista.lb_extrae_info import buscar_requisitos_expediente
from app.libraries.core.inscripcion_lista.lb_req_hv import validar_requisitos_hoja_vida
from app.libraries.core.inscripcion_lista.lb_req_plan_gob import validar_requisitos_plan_gob
from app.libraries.lb_utils import obtener_id_expediente_eleccia, actualizar_estado_requisito
from app.database.models.db_models_eleccia import EstadoRequisitoExpediente
from app.database.models.db_models_eleccia import Candidato

class EstrategiaExpediente:
    """Clase base para las estrategias de expedientes."""
    def procesar_expediente(self, num_expediente: str) -> dict:
        raise NotImplementedError("La estrategia debe implementar el método procesar_expediente.")

class EstrategiaInscripcionLista(EstrategiaExpediente):
    """Estrategia para el manejo de expedientes de inscripción de lista."""
    def procesar_expediente(self, num_expediente: str) -> dict:
        # Crear sesión de base de datos
        db = SessionLocal()
        try:
            # 1. Buscar requisitos a cumplir
            requisitos_lista, requisitos_candidatos, info_validacion_cc = buscar_requisitos_expediente(num_expediente, db)
            
            # 2. Buscar documentos del expediente
            documentos = buscar_documentos(num_expediente)
            if isinstance(documentos, str):
                documentos = json.loads(documentos)
            
            # 3. Buscar información de candidatos
            info_candidatos = buscar_candidatos(num_expediente)
            if isinstance(info_candidatos, str):
                info_candidatos = json.loads(info_candidatos)
            
            documentos_candidatos = buscar_documentos_candidatos(num_expediente)
            if isinstance(documentos_candidatos, str):
                documentos_candidatos = json.loads(documentos_candidatos)
            
            # 4. Validar requisitos
            if info_candidatos and isinstance(info_candidatos, dict) and 'CANDIDATOS' in info_candidatos:
                # Obtener el ubigeo del primer candidato para validaciones
                primer_candidato = next(iter(info_candidatos['CANDIDATOS'].values()))[0]
                ubigeo = primer_candidato['tx_ubigeo_postula']
                lugar_electoral = primer_candidato['tx_postula_region'].split('/')[-1]
                
            # 5. Validar requisitos
            def ejecutar_validacion_lista():
                return validar_requisitos_lista(num_expediente, info_candidatos['CANDIDATOS'], ubigeo, info_validacion_cc, documentos.get('URLS_DOCUMENTOS', {}))

            def ejecutar_validacion_acta():
                return validar_requisitos_acta_interna(num_expediente, info_candidatos, lugar_electoral, documentos.get('URLS_DOCUMENTOS', {}))

            def ejecutar_validacion_hoja_vida():
                return validar_requisitos_hoja_vida(num_expediente, info_candidatos, documentos_candidatos.get('DOCUMENTOS_CANDIDATOS', {}))

            def ejecutar_validacion_plan_gob():
                return validar_requisitos_plan_gob(num_expediente, documentos.get('URLS_DOCUMENTOS', {}))

            # Ejecutar validaciones en paralelo
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_lista = executor.submit(ejecutar_validacion_lista)
                future_acta = executor.submit(ejecutar_validacion_acta)
                future_hoja_vida = executor.submit(ejecutar_validacion_hoja_vida)
                future_plan_gob = executor.submit(ejecutar_validacion_plan_gob)

                # Esperar a que todas las validaciones terminen
                validaciones_lista = future_lista.result()
                validaciones_acta = future_acta.result()
                validaciones_hoja_vida = future_hoja_vida.result()
                validaciones_plan_gob = future_plan_gob.result()

            id_expediente = obtener_id_expediente_eleccia(db, num_expediente)
            
            if not id_expediente:
                raise ValueError(f"No se encontró el expediente {num_expediente} en la base de datos")
            
            # 6. actualizar estado de los requisitos
            # Actualizar estados de requisitos en la base de datos
            print(f"Guardando requisitos para: {num_expediente}")
            for codigo, resultado in validaciones_lista.items():
                actualizar_estado_requisito(
                    db=db,
                    id_expediente=id_expediente,
                    codigo_requisito=codigo,
                    cumple=resultado['cumple'],
                    mensaje=resultado['mensaje'],
                    usuario="ELECCIA",
                    tipo_requisito='LISTA',
                    archivo_ruta=resultado.get('url_documento')
                )

            for codigo, resultado in validaciones_acta.items():
                actualizar_estado_requisito(
                    db=db,
                    id_expediente=id_expediente,
                    codigo_requisito=codigo,
                    cumple=resultado['cumple'],
                    mensaje=resultado['mensaje'],
                    usuario="ELECCIA",
                    tipo_requisito='ACTA',
                    archivo_ruta=resultado.get('url_documento')
                )

            # Procesar resultados de hojas de vida
            for dni, resultado_candidato in validaciones_hoja_vida.items():
                if 'error' in resultado_candidato:
                    print(f"Error en validación de hoja de vida para DNI {dni}: {resultado_candidato['error']}")
                    continue
                
                # Obtener el id_candidato para este DNI
                candidato = db.query(Candidato).filter(Candidato.dni == dni).first()
                if not candidato:
                    print(f"No se encontró el candidato con DNI {dni} en la base de datos")
                    continue
                
                if 'requisitos' in resultado_candidato:
                    for codigo, resultado in resultado_candidato['requisitos'].items():
                        actualizar_estado_requisito(
                            db=db,
                            id_expediente=id_expediente,
                            codigo_requisito=codigo,
                            cumple=resultado['cumple'],
                            mensaje=resultado['mensaje'],
                            usuario="ELECCIA",
                            tipo_requisito='CANDIDATO',
                            archivo_ruta=resultado.get('url_documento', ''),
                            id_candidato=candidato.id_candidato
                        )

            for codigo, resultado in validaciones_plan_gob.items():
                actualizar_estado_requisito(
                    db=db,
                    id_expediente=id_expediente,
                    codigo_requisito=codigo,
                    cumple=resultado['cumple'],
                    mensaje=resultado['mensaje'],
                    usuario="ELECCIA",
                    tipo_requisito='PLAN_GOB',
                    archivo_ruta=resultado.get('url_documento')
                )
            print(f"Requisitos guardados para: {num_expediente}")
            # 7. Calcular totales
            # Obtener el ID del expediente
           
            
            # Consultar los requisitos en la tabla EstadoRequisitoExpediente
            requisitos_db = db.query(EstadoRequisitoExpediente).filter(
                EstadoRequisitoExpediente.id_expediente == id_expediente
            ).all()
            
            # Calcular totales
            total_requisitos = len(requisitos_db)
            requisitos_cumplidos = sum(1 for req in requisitos_db if req.id_estado_validacion == 7)  # 7 = CUMPLE
            requisitos_faltantes = sum(1 for req in requisitos_db if req.id_estado_validacion in [8, 10])  # 8 = NO_CUMPLE, 10 = PENDIENTE
            
            # Verificar que los totales coincidan
            if total_requisitos != (requisitos_cumplidos + requisitos_faltantes):
                print(f"Advertencia: Los totales no coinciden. Total: {total_requisitos}, Cumplidos: {requisitos_cumplidos}, Faltantes: {requisitos_faltantes}")
            
            # Determinar tipo de resolución
            tipo_resolucion = "Resolución de Admisión"
            motivo_resolucion = "Cumple con todos los requisitos esenciales para la inscripción."
            
            # Obtener calificación de la resolución
            from app.services.sr_ia_services import calificacion_resolucion
            import markdown as md
            calificacion = calificacion_resolucion(num_expediente)
            calificacion_md = md.markdown(calificacion.get('analisis', ''))
            # Determinar tipo y motivo de resolución según veredicto
            veredicto = calificacion.get('veredicto', '')
            if veredicto == "IMPROCEDENTE":
                tipo_resolucion = "Resolución de Improcedencia"
                motivo_resolucion = "Incumplimiento de requisitos esenciales de solicitud de inscripción."
            elif veredicto == "INADMISIBLE":
                tipo_resolucion = "Resolución de Inadmisibilidad"
                motivo_resolucion = "Incumplimiento de requisitos formales que pueden ser subsanados."
            else:  # ADMISIBLE
                tipo_resolucion = "Resolución de Admisión"
                motivo_resolucion = "Cumple con todos los requisitos esenciales para la inscripción."
            
            # Guardar resumen en tabla Resolucion
            from app.database.models.db_models_eleccia import Resolucion, Expediente
            from datetime import datetime
            from app.services.sr_ia_services import obtener_normativas
            
            # Obtener normativas para el expediente
            normativas = obtener_normativas(num_expediente)
            if isinstance(normativas, dict) and 'error' in normativas:
                normativas = None
            
            # Convertir el array de normativas a una cadena JSON
            normativas_json = json.dumps(normativas) if normativas else None
            
            # Obtener el ID numérico del expediente
            expediente = db.query(Expediente).filter(Expediente.nombre_expediente == num_expediente).first()
            if not expediente:
                raise ValueError(f"No se encontró el expediente con número {num_expediente}")
            
            # Buscar la última resolución sin archivo
            ultima_resolucion = db.query(Resolucion).filter(
                Resolucion.id_expediente == expediente.id_expediente,
                Resolucion.archivo_resolucion == None
            ).order_by(Resolucion.fecha_creacion.desc()).first()

            if ultima_resolucion:
                # Actualizar la resolución existente
                ultima_resolucion.tipo_resolucion = tipo_resolucion
                ultima_resolucion.id_estado = 3  # Estado 3 como solicitado
                ultima_resolucion.total_requisitos = total_requisitos
                ultima_resolucion.requisitos_cumplidos = requisitos_cumplidos
                ultima_resolucion.requisitos_faltantes = requisitos_faltantes
                ultima_resolucion.descripcion_resolucion = calificacion_md
                ultima_resolucion.motivo_resolucion = motivo_resolucion
                ultima_resolucion.modificado_por = "Sistema"
                ultima_resolucion.normativas = normativas_json
                ultima_resolucion.fecha_modificacion = datetime.now()
            else:
                # Crear nueva resolución si no existe una sin archivo
                ultima_resolucion = Resolucion(
                    id_expediente=expediente.id_expediente,
                    codigo_resolucion=f"RES-{num_expediente}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    tipo_resolucion=tipo_resolucion,
                    id_estado=3,  # Estado 3 como solicitado
                    total_requisitos=total_requisitos,
                    requisitos_cumplidos=requisitos_cumplidos,
                    requisitos_faltantes=requisitos_faltantes,
                    descripcion_resolucion=calificacion_md,
                    motivo_resolucion=motivo_resolucion,
                    creado_por="Sistema",
                    modificado_por="Sistema",
                    normativas=normativas_json
                )
                db.add(ultima_resolucion)
            
            db.commit()
            
            
            return {"success": True}, "views/inscripcion_lista.html"
            
        finally:
            db.close()


