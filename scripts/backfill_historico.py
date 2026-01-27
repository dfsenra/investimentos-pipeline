import yfinance as yf
import pandas as pd
from datetime import datetime
import time

TICKERS = ["FLRY3.SA", "SAPR11.SA", "PSEC11.SA", "KFOF11.SA", "VALE3.SA", "PETR3.SA", "BOVA11.SA"]  # Irei puxar da base de dados na versão final

output_path = "../data/historical/precos_historicos.csv"

all_data = []
failed = []

for ticker in TICKERS:
    try:
        df = yf.download(
            ticker,
            period ="5y",
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            failed.append(ticker)
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()

        df = df.rename(columns={
            "Date": "date",
            "Close": "close",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Volume": "volume"
        })

        df = df[["date", "open", "high", "low", "close", "volume"]]
        df["ticker"] = ticker

        all_data.append(df)
        time.sleep(10)          # Atraso agressivo anti-rate-limit

    except Exception as e:
        failed.append(ticker)
        print(f"Erro no ticker {ticker}: {e}")

# ==============================================================
# Escrita CSV
# ==============================================================
final_df = pd.concat(all_data, ignore_index=True)
final_df.to_csv(output_path, index=False)

print(f"Backfill histórico salvo em: {output_path}")
print(f"Tickers com falha: {failed}")

