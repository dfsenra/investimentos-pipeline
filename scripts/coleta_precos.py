# Módulo com execução manual. Tentei automatizar via cron no docker, mas tive problemas.
# Deixei como manual para o usuário. Ao final o preço do portfólio atualizado (chama o módulo calcula_portfolio.py)

import yfinance as yf
import pandas as pd
from datetime import date
import logging
import os
import time
import smtplib
import sys
from email.message import EmailMessage
from dotenv import load_dotenv
from sqlalchemy import text
from dashboard.db import get_engine


# =====================================================================================
# Configuração básica
# =====================================================================================
load_dotenv()

engine = get_engine()

LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_DIR}/coleta.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

EMAIL_SENHA = os.getenv("EMAIL_SENHA_APP")
EMAIL_REMETENTE = "cervejariagrajau@gmail.com"          # gente, eu faço cerveja em casa e esse é o nome da minha
EMAIL_DESTINO = "dfsenra@gmail.com"                     # cervejaria kkkkkkk     

def enviar_alerta(assunto, corpo):
    msg = EmailMessage()
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = assunto
    msg.set_content(corpo)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)

# =====================================================================================
# Leitura dos tickers
# =====================================================================================
tickers = pd.read_csv("/data/tickers.csv")["ticker"].tolist()

ativos_descartados = []

# =====================================================================================
# Garante tabelas criadas para não quebrar o dashboard
# =====================================================================================
from sqlalchemy import text

with engine.begin() as conn:
    with open("/app/scripts/sql/schema.sql") as f:
        conn.execute(text(f.read()))

# =====================================================================================
# Garante ativos no banco
# =====================================================================================
with engine.begin() as conn:
    for ticker in tickers:
        conn.execute(
            text("""
                INSERT INTO assets (ticker)
                VALUES (:ticker)
                ON CONFLICT (ticker) DO NOTHING
            """),
            {"ticker": ticker}
        )

# =====================================================================================
# Coleta de preços
# =====================================================================================
for ticker in tickers:
    try:
        logging.info(f"Coletando {ticker}")

        df = yf.Ticker(ticker).history(period="3mo", auto_adjust=False)
        df = df[df.index.date < date.today()]

        if df.empty:
            raise ValueError("Sem dados")

        fechamento = round(float(df["Close"].iloc[-1]), 2)
        data_fechamento = df.index[-1].date()

        with engine.begin() as conn:
            asset_id = conn.execute(
                text("SELECT asset_id FROM assets WHERE ticker=:t"),
                {"t": ticker}
            ).scalar()

            conn.execute(
                text("""
                    INSERT INTO prices (asset_id, data, close_price, source)
                    VALUES (:asset_id, :data, :price, 'yfinance')
                    ON CONFLICT (asset_id, data) DO NOTHING
                """),
                {
                    "asset_id": asset_id,
                    "data": data_fechamento,
                    "price": fechamento
                }
            )

        time.sleep(15)

    except Exception as e:
        ativos_descartados.append(f"{ticker}: {e}")
        logging.error(f"{ticker} - {e}")

# =====================================================================================
# Alerta
# =====================================================================================
if ativos_descartados:
    enviar_alerta(
        "Alerta – Falha na coleta",
        "\n".join(ativos_descartados)
    )

# =====================================================================================
# Atualiza o preço médio da carteira
# =====================================================================================
#os.system("python /app/scripts/calcula_portfolio.py")
import subprocess

subprocess.run(
    ["python", "/app/scripts/calcula_portfolio.py"],
    check=True
)


