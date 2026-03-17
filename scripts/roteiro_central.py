import time
import sys
from pathlib import Path
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dashboard.db import get_engine
from scripts.pipeline_incremental import pipeline_incremental


caminho_schema = "/app/scripts/sql/schema.sql"
caminho_views = "/app/scripts/sql/views.sql"
caminho_ativos = "/app/data/indices.csv"

def aguardar_criacao_db(engine, retries=15, delay=3):
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Banco disponível")
            return
        except Exception:
            print(f"Banco indisponível ({i+1}/{retries})...")
            time.sleep(delay)

    raise RuntimeError("Banco não ficou disponível a tempo")


def criar_tabelas(engine):
    print("Criando tabelas do banco...")
    with open(caminho_schema) as f:
        sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("Tabelas criadas")

def criar_views(engine):
    print("Criando views...")
    with open(caminho_views) as f:
        sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("Views criadas")


if __name__ == "__main__":
    engine = get_engine()
    aguardar_criacao_db(engine)
    criar_tabelas(engine)
    criar_views(engine)
    pipeline_incremental(engine)
