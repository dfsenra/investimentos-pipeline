import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

if not DATABASE_URL:
    raise RuntimeError("Variáveis de banco não definidas")

def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)
