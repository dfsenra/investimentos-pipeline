import time
import sys
from pathlib import Path
from sqlalchemy import text

# garante que /app está no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dashboard.db import get_engine
from scripts.backfill_historico import run_backfill


SCHEMA_PATH = "/app/scripts/sql/schema.sql"
VIEWS_PATH = "/app/scripts/sql/views.sql"

def wait_for_db(engine, retries=15, delay=3):
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


def create_schema(engine):
    print("Criando schema do banco...")
    with open(SCHEMA_PATH) as f:
        sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("Schema criado")

def create_views(engine):
    print("Criando views...")
    with open(VIEWS_PATH) as f:
        sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(sql))

    print("Views criadas")


if __name__ == "__main__":
    engine = get_engine()
    wait_for_db(engine)
    create_schema(engine)
    create_views(engine)
    run_backfill(engine)
