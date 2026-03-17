import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
from sqlalchemy import text
import logging
import os
from dashboard.db import get_engine 

caminho_ativos = "/data/indices.csv"
caminho_log = "/app/logs"
os.makedirs(caminho_log, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(f"{caminho_log}/backfill.log"),
        logging.StreamHandler()
    ]
)

logging.raiseExceptions = False

def carrega_tickers(engine):
    logging.info("Carregando os tickers do banco de dados...")
    
    with engine.connect() as conn:
        df_ativos = pd.read_sql("SELECT ticker, tipo_ativo FROM ativos", conn)

    if os.path.exists(caminho_ativos):
        try:
            indices_csv = pd.read_csv(caminho_ativos)
            indices_csv["tipo_ativo"] = "indice"
            df = pd.concat([df_ativos, indices_csv], ignore_index=True)
        except Exception as e:
            logging.warning(f"Erro ao ler CSV de índices: {e}")
            df = df_ativos
    else:
        df = df_ativos

    df = df.drop_duplicates(subset=['ticker']).dropna(subset=['ticker'])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df


def coleta_ultima_data(engine, ticker):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT MAX(p.data)
                FROM precos p
                JOIN ativos a ON a.id_ativo = p.id_ativo
                WHERE a.ticker = :ticker
            """),
            {"ticker": ticker}
        ).scalar()
    return result


# Remove preços de ativos que não estão mais na tabela ativos
def limpeza_ativos_ausentes(engine):
    
    query = text("""
        DELETE FROM precos 
        WHERE id_ativo NOT IN (SELECT id_ativo FROM ativos);
    """)
    with engine.begin() as conn:
        result = conn.execute(query)
        logging.info(f"Limpeza: {result.rowcount} registros de preços de ativos ausentes foram removidos.")


def pipeline_incremental(engine=None):
    if engine is None:
        engine = get_engine()
    
    logging.info("Iniciando o pipeline incremental...")
    df_ativos = carrega_tickers(engine)
    hoje = datetime.now().date()

    for _, row in df_ativos.iterrows():
        ticker = row["ticker"]
        tipo_ativo = row["tipo_ativo"]
        
        try:
            # Garante que o ativo existe e coelta o ID dele
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO ativos (ticker, tipo_ativo) VALUES (:t, :type) ON CONFLICT (ticker) DO NOTHING"),
                    {"t": ticker, "type": tipo_ativo}
                )
                id_ativo = conn.execute(
                    text("SELECT id_ativo FROM ativos WHERE ticker = :t"),
                    {"t": ticker}
                ).scalar()

            ultima_data = coleta_ultima_data(engine, ticker)

            dia_semana = hoje.weekday()

            if dia_semana == 0:
                # Se rodar o pipeline no sábado, domingo ou segunda feira, o alvo é a sexta (último pregão)
                alvo_ultimo_dado = hoje - timedelta(days=3)
            elif dia_semana == 6:
                alvo_ultimo_dado = hoje - timedelta(days=2)
            else:
                alvo_ultimo_dado = hoje - timedelta(days=1)

            if ultima_data:
                if ultima_data >= alvo_ultimo_dado:
                    logging.info(f"{ticker} já está atualizado com dados de {ultima_data}.")
                    continue

                data_inicio = ultima_data + timedelta(days=1)
                logging.info(f"{ticker}: Atualizando de {data_inicio} até {hoje}")
                
            else:
                data_inicio = hoje - timedelta(days=5 * 365)
                logging.info(f"{ticker} (ID:{id_ativo}): Novo. Baixando histórico completo...")

            df_yfinance = yf.download(ticker, start=data_inicio, end=hoje + timedelta(days=1), auto_adjust=True, progress=False)

            if df_yfinance.empty:
                logging.warning(f"{ticker}: Nenhum dado encontrado no Yahoo Finance.")
                continue

            df_yfinance = df_yfinance.reset_index()
            
            if isinstance(df_yfinance.columns, pd.MultiIndex):
                df_yfinance.columns = [col[0] if col[0] != '' else col[1] for col in df_yfinance.columns]
            
            df_yfinance.columns = [col.lower().strip() for col in df_yfinance.columns]
            
            rename_map = {
                "date": "data", "open": "preco_abertura", "high": "preco_max",
                "low": "preco_min", "close": "preco_fechamento"
            }
            df_yfinance = df_yfinance.rename(columns=rename_map)

            registros_inseridos = 0
            with engine.begin() as conn:
                for _, p_row in df_yfinance.iterrows():
                    fechamento_pregao = p_row.get("preco_fechamento")
                    if pd.isna(fechamento_pregao): continue

                    conn.execute(
                        text("""
                            INSERT INTO precos (
                                id_ativo, data, preco_abertura, preco_max, 
                                preco_min, preco_fechamento, volume, fonte
                            )
                            VALUES (
                                :id_ativo, :data, :open, :high, 
                                :low, :close, :volume, 'yfinance'
                            )
                            ON CONFLICT (id_ativo, data) DO NOTHING
                        """),
                        {
                            "id_ativo": id_ativo,
                            "data": p_row["data"].date(),
                            "open": p_row.get("preco_abertura"),
                            "high": p_row.get("preco_max"),
                            "low": p_row.get("preco_min"),
                            "close": fechamento_pregao,
                            "volume": int(p_row["volume"]) if pd.notnull(p_row.get("volume")) else 0,
                        }
                    )
                    registros_inseridos += 1
            
            logging.info(f"{ticker}: {registros_inseridos} novos dias salvos.")
            time.sleep(0.5)

        except Exception as e:
            logging.error(f"Erro crítico no ticker {ticker}: {str(e)}")

    logging.info("Pipeline finalizado!")

if __name__ == "__main__":
    main_engine = get_engine()
    pipeline_incremental(main_engine)
    limpeza_ativos_ausentes(main_engine)