import pandas as pd
from sqlalchemy import text
# Atualiza o último preço para o portfólio (todos ativos juntos)
# Esse módulo é chamado pelo coleta_precos.py

from dashboard.db import get_engine

engine = get_engine()

query = """
SELECT
    p.data,
    a.ticker,
    p.close_price
FROM prices p
JOIN assets a ON a.asset_id = p.asset_id
ORDER BY p.data
"""

df = pd.read_sql(query, engine)

# Normalização base 100 por ativo
df["base"] = df.groupby("ticker")["close_price"].transform("first")
df["normalized"] = df["close_price"] / df["base"] * 100

portfolio = (
    df.groupby("data")["normalized"]
    .mean()
    .reset_index()
    .rename(columns={"normalized": "portfolio_price"})
)

with engine.begin() as conn:
    for _, row in portfolio.iterrows():
        conn.execute(
            text("""
                INSERT INTO portfolio_daily (date, portfolio_price)
                VALUES (:date, :price)
                ON CONFLICT (date) DO UPDATE
                SET portfolio_price = EXCLUDED.portfolio_price
            """),
            {
                "date": row["data"],
                "price": row["portfolio_price"]
            }
        )
