import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales desde variables de entorno
nombre_usuario = os.getenv("DB_USER")
contraseña = os.getenv("DB_PASS")
dsn = os.getenv("DB_DSN")

# Crear motor de base de datos para Oracle
motor = create_engine(f"oracle+cx_oracle://{nombre_usuario}:{contraseña}@{dsn}", pool_pre_ping=True, pool_size=30, max_overflow=20, pool_timeout=120)

# Configurar la sesión de la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)
Base = declarative_base()

# Dependencia para obtener la sesión de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Segunda conexión (ROP)
DB_USER_ROP = os.getenv("DB_USER_ROP")
DB_PASS_ROP = os.getenv("DB_PASS_ROP")
DB_DSN_ROP = os.getenv("DB_DSN_ROP")

engine_rop = create_engine(f"oracle+cx_oracle://{DB_USER_ROP}:{DB_PASS_ROP}@{DB_DSN_ROP}", pool_pre_ping=True, pool_size=5, max_overflow=10, pool_timeout=90)
SessionLocalROP = sessionmaker(autocommit=False, autoflush=False, bind=engine_rop)

Base_rop = declarative_base()

# Configurar la sesión de la base de datos
def get_db_rop():
    db = SessionLocalROP()
    try:
        yield db
    finally:
        db.close()