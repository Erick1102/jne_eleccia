from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_session import Base

class Estado(Base):
    __tablename__ = "ELECCIA_TRF_ESTADOS"
    
    id_estado = Column(Integer, primary_key=True, autoincrement=True)
    nombre_estado = Column(String(100), nullable=False)
    descripcion = Column(Text)
    entidad_relacionada = Column(String(100), nullable=False)
    es_activo = Column(Boolean, default=True)


class TipoExpediente(Base):
    __tablename__ = "ELECCIA_TRF_TIPOS_EXPEDIENTES"
    
    id_tipo_expediente = Column(Integer, primary_key=True, autoincrement=True)
    nombre_tipo_expediente = Column(String(255), nullable=False)
    descripcion = Column(Text)
    creado_por = Column(String(255))
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    modificado_por = Column(String(255))
    
    # Relaciones existentes
    requisitos_tipos_expedientes_materias = relationship("RequisitoTipoExpedienteMateria", back_populates="tipo_expediente")
    expedientes_tipos_expedientes_materias = relationship("ExpedienteTipoExpedienteMateria", back_populates="tipo_expediente")

class Materia(Base):
    __tablename__ = "ELECCIA_TRF_MATERIAS"
    
    id_materia = Column(Integer, primary_key=True, autoincrement=True)
    nombre_materia = Column(String(255), nullable=False)
    descripcion = Column(Text)
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    # Relaciones existentes
    requisitos_tipos_expedientes_materias = relationship("RequisitoTipoExpedienteMateria", back_populates="materia")
    expedientes_tipos_expedientes_materias = relationship("ExpedienteTipoExpedienteMateria", back_populates="materia")

class Requisito(Base):
    __tablename__ = "ELECCIA_TRF_REQUISITOS"
    
    id_requisito = Column(Integer, primary_key=True, autoincrement=True)
    nombre_requisito = Column(String(255), nullable=False)
    descripcion = Column(Text)
    metodo_validacion = Column(String(255))
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    # Relaciones existentes
    requisitos_tipos_expedientes_materias = relationship("RequisitoTipoExpedienteMateria", back_populates="requisito")

class RequisitoTipoExpedienteMateria(Base):
    __tablename__ = "ELECCIA_TBL_REQ_TIPO_EXP_MAT"
    
    id_requisito_tipo_expediente_materia = Column(Integer, primary_key=True, autoincrement=True)
    id_tipo_expediente = Column(Integer, ForeignKey("ELECCIA_TRF_TIPOS_EXPEDIENTES.id_tipo_expediente"), nullable=False)
    id_materia = Column(Integer, ForeignKey("ELECCIA_TRF_MATERIAS.id_materia"), nullable=False)
    id_requisito = Column(Integer, ForeignKey("ELECCIA_TRF_REQUISITOS.id_requisito"), nullable=False)
    nombre_requisito = Column(String(255))
    descripcion = Column(Text)
    metodo_validacion = Column(String(255))
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    # Relaciones
    tipo_expediente = relationship("TipoExpediente", back_populates="requisitos_tipos_expedientes_materias")
    materia = relationship("Materia", back_populates="requisitos_tipos_expedientes_materias")
    requisito = relationship("Requisito", back_populates="requisitos_tipos_expedientes_materias")
    estados_requisitos = relationship("EstadoRequisitoExpediente", back_populates="requisito_tipo_expediente_materia")

class Expediente(Base):
    __tablename__ = "ELECCIA_TRF_EXPEDIENTES"
    
    id_expediente = Column(Integer, primary_key=True, autoincrement=True)
    nombre_expediente = Column(String(255), nullable=False)
    descripcion = Column(Text)
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    creado_por = Column(String(255))
    creado_en = Column(DateTime, default=func.current_timestamp())
    modificado_por = Column(String(255))
    modificado_en = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    expedientes_tipos_expedientes_materias = relationship("ExpedienteTipoExpedienteMateria", back_populates="expediente")
    estados = relationship("EstadoExpediente", back_populates="expediente")
    resoluciones = relationship("Resolucion", back_populates="expediente")

class ExpedienteTipoExpedienteMateria(Base):
    __tablename__ = "ELECCIA_TBL_EXP_TIPO_EXP_MAT"
    
    id_expediente_tipo_expediente_materia = Column(Integer, primary_key=True, autoincrement=True)
    id_expediente = Column(Integer, ForeignKey("ELECCIA_TRF_EXPEDIENTES.id_expediente"), nullable=False)
    id_tipo_expediente = Column(Integer, ForeignKey("ELECCIA_TRF_TIPOS_EXPEDIENTES.id_tipo_expediente"), nullable=False)
    id_materia = Column(Integer, ForeignKey("ELECCIA_TRF_MATERIAS.id_materia"), nullable=False)
    analisis_realizado = Column(Boolean)
    total_requisitos = Column(Integer)
    requisitos_cumplidos = Column(Integer)
    requisitos_faltantes = Column(Integer)
    porcentaje_cumplimiento = Column(Float(precision=5))
    mensaje_alerta = Column(Text)
    tipo_resolucion = Column(String(255))
    motivo_resolucion = Column(Text)
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_modificacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    # Relaciones
    expediente = relationship("Expediente", back_populates="expedientes_tipos_expedientes_materias")
    tipo_expediente = relationship("TipoExpediente", back_populates="expedientes_tipos_expedientes_materias")
    materia = relationship("Materia", back_populates="expedientes_tipos_expedientes_materias")
    estados_requisitos = relationship("EstadoRequisitoExpediente", back_populates="expediente_tipo_expediente_materia")

class EstadoRequisitoExpediente(Base):
    __tablename__ = "ELECCIA_TBL_ESTADO_REQ_EXP"
    
    id_estado_requisito = Column(Integer, primary_key=True, autoincrement=True)
    id_expediente_tipo_expediente_materia = Column(Integer, ForeignKey("ELECCIA_TBL_EXP_TIPO_EXP_MAT.id_expediente_tipo_expediente_materia"), nullable=False)
    id_requisito_tipo_expediente_materia = Column(Integer, ForeignKey("ELECCIA_TBL_REQ_TIPO_EXP_MAT.id_requisito_tipo_expediente_materia"), nullable=False)
    estado = Column(String(10), nullable=False)
    observaciones = Column(Text)
    id_estado_sistema = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado_sistema = relationship("Estado")
    fecha_actualizacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    actualizado_por = Column(String(255))
    
    # Relaciones
    expediente_tipo_expediente_materia = relationship("ExpedienteTipoExpedienteMateria", back_populates="estados_requisitos")
    requisito_tipo_expediente_materia = relationship("RequisitoTipoExpedienteMateria", back_populates="estados_requisitos")

class EstadoExpediente(Base):
    __tablename__ = "ELECCIA_TBL_ESTADO_EXP"
    
    id_estado_expediente = Column(Integer, primary_key=True, autoincrement=True)
    id_expediente = Column(Integer, ForeignKey("ELECCIA_TRF_EXPEDIENTES.id_expediente"), nullable=False)
    estado = Column(String(20), nullable=False)
    id_estado_sistema = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado_sistema = relationship("Estado")
    fecha_actualizacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    actualizado_por = Column(String(255))
    
    # Relaciones
    expediente = relationship("Expediente", back_populates="estados")

class Resolucion(Base):
    __tablename__ = "ELCCIA_TBL_RESOLUCIONES"
    
    id_resolucion = Column(Integer, primary_key=True, autoincrement=True)
    id_expediente = Column(Integer, ForeignKey("ELECCIA_TRF_EXPEDIENTES.id_expediente"), nullable=False)
    estado_resolucion = Column(String(15), nullable=False)
    tipo_resolucion = Column(String(255))
    descripcion_resolucion = Column(Text)
    id_estado = Column(Integer, ForeignKey("ELECCIA_TRF_ESTADOS.id_estado"))
    estado = relationship("Estado")
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    creado_por = Column(String(255))
    modificado_por = Column(String(255))
    
    # Relaciones
    expediente = relationship("Expediente", back_populates="resoluciones")