import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

url_db = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

if not url_db:
    raise RuntimeError("Variáveis de banco não definidas")

def get_engine():
    return create_engine(url_db, pool_pre_ping=True)
