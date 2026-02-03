import pandas as pd
from sqlalchemy import text
from dashboard.db import get_engine

CSV_PATH = "/data/tickers.csv"

engine = get_engine()

def ingest_portfolio():
    df = pd.read_csv(CSV_PATH)

    required_cols = {"ticker", "data_compra", "quantidade", "preco_compra"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV precisa conter: {required_cols}")

    df["data_compra"] = pd.to_datetime(df["data_compra"]).dt.date

    with engine.begin() as conn:
        for _, row in df.iterrows():
            asset_id = conn.execute(
                text("SELECT asset_id FROM assets WHERE ticker = :ticker"),
                {"ticker": row["ticker"]}
            ).scalar()

            if asset_id is None:
                raise ValueError(f"Ticker não encontrado em assets: {row['ticker']}")

            conn.execute(
                text("""
                    INSERT INTO portfolio_transactions (
                        asset_id,
                        data_compra,
                        quantidade,
                        preco_compra
                    )
                    VALUES (
                        :asset_id,
                        :data_compra,
                        :quantidade,
                        :preco_compra
                    )
                """),
                {
                    "asset_id": asset_id,
                    "data_compra": row["data_compra"],
                    "quantidade": row["quantidade"],
                    "preco_compra": row["preco_compra"],
                }
            )

    print("✔ Portfolio carregado com sucesso")


if __name__ == "__main__":
    ingest_portfolio()
