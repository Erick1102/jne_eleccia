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
motor = create_engine(f"oracle+cx_oracle://{nombre_usuario}:{contraseña}@{dsn}")

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
