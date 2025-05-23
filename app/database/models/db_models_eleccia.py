from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.db_session import Base


class Estado(Base):
    __tablename__ = 'ELECCIA_TRF_ESTADOS'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_estado = Column(Integer, primary_key=True)
    codigo_estado = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    es_activo = Column(Integer, default=1)
    tipo_estado = Column(String(50), nullable=False)


class TipoExpediente(Base):
    __tablename__ = 'ELECCIA_TRF_TIPOS_EXPEDIENTES'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_tipo_expediente = Column(Integer, primary_key=True)
    codigo_tipo_expediente = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    id_estado = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'))
    creado_por = Column(String(255))
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    modificado_por = Column(String(255))
    
    estado = relationship("Estado")


class Materia(Base):
    __tablename__ = 'ELECCIA_TRF_MATERIAS'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_materia = Column(Integer, primary_key=True)
    codigo_materia = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    id_estado = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'))
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    estado = relationship("Estado")


class Requisito(Base):
    __tablename__ = 'ELECCIA_TRF_REQUISITOS'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_requisito = Column(Integer, primary_key=True)
    codigo_requisito = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    id_estado = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'))
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    nombre_requisito = Column(String(100))
    
    estado = relationship("Estado")


class ConfiguracionRequisito(Base):
    __tablename__ = 'ELECCIA_TBL_REQUISITOS_TIPO_EXP_MAT'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_configuracion = Column(Integer, primary_key=True)
    id_tipo_expediente = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_TIPOS_EXPEDIENTES.id_tipo_expediente'), nullable=False)
    id_materia = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_MATERIAS.id_materia'), nullable=False)
    id_requisito = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_REQUISITOS.id_requisito'), nullable=False)
    es_obligatorio = Column(Integer, default=1)
    prioridad = Column(Integer)
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    creado_por = Column(String(255))    
    
    tipo_expediente = relationship("TipoExpediente")
    materia = relationship("Materia")
    requisito = relationship("Requisito")


class Expediente(Base):
    __tablename__ = 'ELECCIA_TBL_EXPEDIENTES'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_expediente = Column(Integer, primary_key=True)
    numero_expediente = Column(String(100), nullable=False, unique=True)
    nombre_expediente = Column(String(255), nullable=False)
    descripcion = Column(Text)
    id_tipo_expediente = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_TIPOS_EXPEDIENTES.id_tipo_expediente'), nullable=False)
    id_materia = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_MATERIAS.id_materia'), nullable=False)
    id_estado = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'), nullable=False)
    usuario_asignado = Column(String(255))
    creado_por = Column(String(255))
    creado_en = Column(DateTime, default=func.current_timestamp())
    modificado_por = Column(String(255))
    modificado_en = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    tipo_expediente = relationship("TipoExpediente")
    materia = relationship("Materia")
    estado = relationship("Estado")
    resoluciones = relationship("Resolucion", back_populates="expediente")


class Candidato(Base):
    __tablename__ = 'ELECCIA_TBL_CANDIDATOS'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_candidato = Column(Integer, primary_key=True)
    dni = Column(String(8), nullable=False, unique=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    sexo = Column(String(20), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    direccion = Column(String(255), nullable=False)
    ubigeo = Column(String(6), nullable=False)
    puesto_postula = Column(String(255), nullable=False)
    numero_lista = Column(Integer)
    id_estado = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'), nullable=False)
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    estado = relationship("Estado")
    educaciones = relationship("EducacionCandidato", back_populates="candidato")
    bienes = relationship("BienCandidato", back_populates="candidato")
    historial_laboral = relationship("HistorialLaboral", back_populates="candidato")


class EducacionCandidato(Base):
    __tablename__ = 'ELECCIA_TBL_EDUCACION_CANDIDATOS'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_educacion = Column(Integer, primary_key=True)
    id_candidato = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_CANDIDATOS.id_candidato'), nullable=False)
    nivel_educativo = Column(String(100), nullable=False)
    centro_educativo = Column(String(255), nullable=False)
    especialidad = Column(String(255))
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    titulo_obtenido = Column(String(255))
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    creado_por = Column(String(255))
    
    candidato = relationship("Candidato", back_populates="educaciones")


class BienCandidato(Base):
    __tablename__ = 'ELECCIA_TBL_BIENES_CANDIDATOS'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_bien = Column(Integer, primary_key=True)
    id_candidato = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_CANDIDATOS.id_candidato'), nullable=False)
    tipo_bien = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=False)
    valor = Column(Numeric(15, 2))
    fecha_adquisicion = Column(Date)
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    creado_por = Column(String(255))
    
    candidato = relationship("Candidato", back_populates="bienes")


class HistorialLaboral(Base):
    __tablename__ = 'ELECCIA_TBL_HISTORIAL_LABORAL'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_historial = Column(Integer, primary_key=True)
    id_candidato = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_CANDIDATOS.id_candidato'), nullable=False)
    empresa = Column(String(255), nullable=False)
    cargo = Column(String(255), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    funciones = Column(Text)
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    creado_por = Column(String(255))
    
    candidato = relationship("Candidato", back_populates="historial_laboral")

class EstadoRequisitoExpediente(Base):
    __tablename__ = 'ELECCIA_TBL_ESTADO_REQUISITOS_EXP'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_estado_requisito = Column(Integer, primary_key=True)
    id_expediente = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_EXPEDIENTES.id_expediente'), nullable=False)
    id_configuracion = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_REQUISITOS_TIPO_EXP_MAT.id_configuracion'), nullable=False)
    id_candidato = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_CANDIDATOS.id_candidato'), nullable=True)
    tipo_requisito = Column(String(50), nullable=False)  # LISTA, CANDIDATO, ACTA, PLAN_GOBIERNO
    id_estado_validacion = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'), nullable=False)
    validacion_anterior = Column(String(50))    
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    validado_por = Column(String(50))
    archivo_ruta = Column(String(100))
    observaciones = Column(Text)
    
    expediente = relationship("Expediente")
    configuracion = relationship("ConfiguracionRequisito")
    candidato = relationship("Candidato")
    estado_validacion = relationship("Estado")


class Resolucion(Base):
    __tablename__ = 'ELECCIA_TBL_RESOLUCIONES'
    __table_args__ = {'schema': 'ELECCIA'}
    
    id_resolucion = Column(Integer, primary_key=True)
    id_expediente = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TBL_EXPEDIENTES.id_expediente'), nullable=False)
    codigo_resolucion = Column(String(100), nullable=False, unique=True)
    tipo_resolucion = Column(String(255))
    id_estado = Column(Integer, ForeignKey('ELECCIA.ELECCIA_TRF_ESTADOS.id_estado'), nullable=False)
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    total_requisitos = Column(Integer)
    requisitos_cumplidos = Column(Integer)
    requisitos_faltantes = Column(Integer)
    archivo_resolucion = Column(String(200))
    descripcion_resolucion = Column(Text)
    motivo_resolucion = Column(Text)
    normativas = Column(Text)
    
    expediente = relationship("Expediente", back_populates="resoluciones")
    estado = relationship("Estado")