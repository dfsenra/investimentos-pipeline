import yfinance as yf
import pandas as pd
import time
from sqlalchemy import text

TICKERS = [                    # provisório, irei pegar direto do tickers.csv ao final quando definir a coleta
    # Ativos                   # do Ibovespa e CDI
    "FLRY3.SA",
    "SAPR11.SA",
    "PSEC11.SA",
    "KFOF11.SA",
    "VALE3.SA",
    "PETR3.SA",

    # Índices
    "BOVA11.SA",   # Pelo o que pesquisei esse não é o ibovespa de fato, irei mudar
    "^GSPC",       # S&P500
    "CDI"          # Irei adicionar depois
]


def run_backfill(engine):
    print("Iniciando backfill histórico")

    with engine.begin() as conn:
        for ticker in TICKERS:
            conn.execute(
                text("""
                    INSERT INTO assets (ticker)
                    VALUES (:ticker)
                    ON CONFLICT (ticker) DO NOTHING
                """),
                {"ticker": ticker}
            )

    for ticker in TICKERS:
        if ticker == "CDI":
            print("CDI será adicionado depois (não esquecer!)")
            continue

        try:
            print(f"Baixando histórico: {ticker}")

            df = yf.download(
                ticker,
                period="5y",
                auto_adjust=True,
                progress=False
            )

            if df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index().rename(columns={
                "Date": "data",
                "Open": "open_price",
                "High": "high_price",
                "Low": "low_price",
                "Close": "close_price",
                "Volume": "volume"
            })

            df["data"] = df["data"].dt.date

            with engine.begin() as conn:
                asset_id = conn.execute(
                    text("SELECT asset_id FROM assets WHERE ticker = :ticker"),
                    {"ticker": ticker}
                ).scalar()

                for _, row in df.iterrows():
                    conn.execute(
                        text("""
                            INSERT INTO prices (
                                asset_id, data,
                                open_price, high_price, low_price,
                                close_price, volume, source
                            )
                            VALUES (
                                :asset_id, :data,
                                :open, :high, :low,
                                :close, :volume, 'yfinance'
                            )
                            ON CONFLICT (asset_id, data) DO NOTHING
                        """),
                        {
                            "asset_id": asset_id,
                            "data": row["data"],
                            "open": row["open_price"],
                            "high": row["high_price"],
                            "low": row["low_price"],
                            "close": row["close_price"],
                            "volume": int(row["volume"]),
                        }
                    )

            time.sleep(3)

        except Exception as e:
            print(f"Erro no ticker {ticker}: {e}")

    print("Backfill finalizado")
