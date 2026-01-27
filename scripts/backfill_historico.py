import yfinance as yf
import pandas as pd
from datetime import datetime
import time

TICKERS = ["FLRY3.SA", "SAPR11.SA", "PSEC11.SA", "KFOF11.SA", "VALE3.SA", "PETR3.SA", "IBOV.SA"]  # Irei puxar da base de dados na versão final
START_DATE = "2019-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")

output_path = "../data/historical/precos_historicos.csv"

all_data = []

for ticker in TICKERS:
    df = yf.download(
        ticker,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=False,
        progress=False
    )

    if df.empty:
        continue

    df = df.reset_index()
    df["ticker"] = ticker

    df = df.rename(columns={
        "Date": "date",
        "Adj Close": "adj_close",
        "Close": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Volume": "volume"
    })

    all_data.append(df)
    time.sleep(15)          # Atraso agressivo anti-rate-limit

# ==============================================================
# Escrita CSV
# ==============================================================
final_df = pd.concat(all_data, ignore_index=True)
final_df.to_csv(output_path, index=False)

print(f"Backfill histórico salvo em: {output_path}")
