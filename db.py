from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_settings import DB_SETTINGS

pg = DB_SETTINGS['postgresql']
DATABASE_URL = f"postgresql+psycopg2://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['dbname']}"

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
