import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
from sqlalchemy import text
import logging
import os
from dashboard.db import get_engine 

# Configurações de Caminhos
INDICES_PATH = "/data/indices.csv"
LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/backfill.log"),
        logging.StreamHandler()
    ]
)

logging.raiseExceptions = False

def load_tickers(engine):
    logging.info("Carregando tickers do banco de dados...")
    
    with engine.connect() as conn:
        df_assets = pd.read_sql("SELECT ticker, asset_type FROM assets", conn)

    if os.path.exists(INDICES_PATH):
        try:
            indices_csv = pd.read_csv(INDICES_PATH)
            indices_csv["asset_type"] = "indice"
            df = pd.concat([df_assets, indices_csv], ignore_index=True)
        except Exception as e:
            logging.warning(f"Erro ao ler CSV de índices: {e}")
            df = df_assets
    else:
        df = df_assets

    df = df.drop_duplicates(subset=['ticker']).dropna(subset=['ticker'])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df

def get_last_date(engine, ticker):
    with engine.connect() as conn: # Alterado para connect simples para leitura
        result = conn.execute(
            text("""
                SELECT MAX(p.data)
                FROM prices p
                JOIN assets a ON a.asset_id = p.asset_id
                WHERE a.ticker = :ticker
            """),
            {"ticker": ticker}
        ).scalar()
    return result

def cleanup_orphaned_prices(engine):
    """Remove preços de ativos que não estão mais na tabela assets."""
    query = text("""
        DELETE FROM prices 
        WHERE asset_id NOT IN (SELECT asset_id FROM assets);
    """)
    with engine.begin() as conn:
        result = conn.execute(query)
        logging.info(f"🧹 Limpeza: {result.rowcount} registros de preços órfãos removidos.")


def run_backfill(engine=None):
    if engine is None:
        engine = get_engine()
    
    logging.info("Iniciando backfill incremental...")
    assets_df = load_tickers(engine)
    today = datetime.now().date()

    for _, row in assets_df.iterrows():
        ticker = row["ticker"]
        asset_type = row["asset_type"]
        
        try:
            # 1. GARANTE QUE O ATIVO EXISTE E PEGA O ID
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO assets (ticker, asset_type) VALUES (:t, :type) ON CONFLICT (ticker) DO NOTHING"),
                    {"t": ticker, "type": asset_type}
                )
                asset_id = conn.execute(
                    text("SELECT asset_id FROM assets WHERE ticker = :t"),
                    {"t": ticker}
                ).scalar()

            # 2. VERIFICA ÚLTIMA DATA
            last_date = get_last_date(engine, ticker)

            dia_semana = today.weekday()

            if dia_semana == 0:  # Segunda-feira
                # Na segunda antes do mercado abrir/consolidar, o alvo é a sexta (3 dias atrás)
                alvo_ultimo_dado = today - timedelta(days=3)
            elif dia_semana == 6: # Domingo
                alvo_ultimo_dado = today - timedelta(days=2)
            else:
                alvo_ultimo_dado = today - timedelta(days=1)

            if last_date:
                if last_date >= alvo_ultimo_dado:
                    logging.info(f"✅ {ticker} já atualizado com dados de {last_date}.")
                    continue

                start_date = last_date + timedelta(days=1)
                logging.info(f"🔄 {ticker}: Atualizando de {start_date} até {today}")
                
            else:
                start_date = today - timedelta(days=5 * 365)
                logging.info(f"🚀 {ticker} (ID:{asset_id}): Novo. Baixando histórico completo...")

            # 3. DOWNLOAD (Ajustado para versões novas do yfinance)
            df = yf.download(ticker, start=start_date, end=today + timedelta(days=1), auto_adjust=True, progress=False)

            if df.empty:
                logging.warning(f"⚠️ {ticker}: Nenhum dado encontrado no Yahoo Finance.")
                continue

            # --- TRATAMENTO ROBUSTO DE COLUNAS ---
            df = df.reset_index()
            
            # Se o yfinance retornar MultiIndex (comum em versões recentes), achata:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] if col[0] != '' else col[1] for col in df.columns]
            
            df.columns = [col.lower().strip() for col in df.columns]
            
            # Mapeamento para garantir consistência com o seu banco
            rename_map = {
                "date": "data", "open": "open_price", "high": "high_price",
                "low": "low_price", "close": "close_price"
            }
            df = df.rename(columns=rename_map)

            # 4. SALVAMENTO (Batch update é mais rápido que linha a linha)
            registros_inseridos = 0
            with engine.begin() as conn:
                for _, p_row in df.iterrows():
                    # Garantir que temos os preços mínimos necessários
                    close_p = p_row.get("close_price")
                    if pd.isna(close_p): continue

                    conn.execute(
                        text("""
                            INSERT INTO prices (
                                asset_id, data, open_price, high_price, 
                                low_price, close_price, volume, source
                            )
                            VALUES (
                                :asset_id, :data, :open, :high, 
                                :low, :close, :volume, 'yfinance'
                            )
                            ON CONFLICT (asset_id, data) DO NOTHING
                        """),
                        {
                            "asset_id": asset_id,
                            "data": p_row["data"].date(),
                            "open": p_row.get("open_price"),
                            "high": p_row.get("high_price"),
                            "low": p_row.get("low_price"),
                            "close": close_p,
                            "volume": int(p_row["volume"]) if pd.notnull(p_row.get("volume")) else 0,
                        }
                    )
                    registros_inseridos += 1
            
            logging.info(f"💾 {ticker}: {registros_inseridos} novos dias salvos.")
            time.sleep(0.5)

        except Exception as e:
            logging.error(f"❌ Erro crítico no ticker {ticker}: {str(e)}")

    logging.info("🏁 Backfill finalizado!")

if __name__ == "__main__":
    main_engine = get_engine()
    run_backfill(main_engine)
    cleanup_orphaned_prices(main_engine)