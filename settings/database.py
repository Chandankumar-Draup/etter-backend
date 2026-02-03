import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

POSTGRES_HOST = os.environ.get('ETTER_DB_HOST')
POSTGRES_PORT = os.environ.get('ETTER_DB_PORT')
POSTGRES_USER = os.environ.get('ETTER_DB_USER')
POSTGRES_PASSWORD = os.environ.get('ETTER_DB_PASSWORD')
POSTGRES_DB = os.environ.get('ETTER_DB_NAME')

DATABASE_URL = URL.create(
    drivername="postgresql",
    username=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    port=POSTGRES_PORT
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
