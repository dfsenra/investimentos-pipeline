import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Financial Dashboard", layout="wide")

# ======================================================
# Carregando dados
# ======================================================
@st.cache_data
def load_data():
    df = pd.read_csv("data/historical/precos_historicos.csv", parse_dates=["date"])
    
    df = df.dropna(subset=["date", "close", "ticker"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    return df

df = load_data()

st.title("Financial Asset Explorer")


# ======================================================
# Sidebar - filtros
# ======================================================
st.sidebar.header("Filters")

ticker = st.sidebar.selectbox(
    "Select ticker",
    sorted(df["ticker"].dropna().astype(str).unique())
)

period = st.sidebar.selectbox(
    "Select period",
    [
        "Last 1 month",
        "Last 3 months",
        "Last 6 months",
        "YTD",
        "Last 1 year",
        "Last 5 years"
    ]
)

def resolve_period(period, df):
    end = df["date"].max()

    if period == "Last 1 month":
        start = end - pd.DateOffset(months=1)
    elif period == "Last 3 months":
        start = end - pd.DateOffset(months=3)
    elif period == "Last 6 months":
        start = end - pd.DateOffset(months=6)
    elif period == "YTD":
        start = pd.Timestamp(end.year, 1, 1)
    elif period == "Last 1 year":
        start = end - pd.DateOffset(years=1)
    else:
        start = end - pd.DateOffset(years=5)

    return start, end

def normalize_series(series):
    return (series / series.iloc[0]) * 100

benchmarks = st.sidebar.multiselect(
    "Select benchmark",
    ["Ibovespa", "CDI"]
)

# ======================================================
# Datas - filtros
# ======================================================
start_date, end_date = resolve_period(period, df)

filtered = (
    df[df["ticker"] == ticker]
    .loc[lambda x: (x["date"] >= start_date) & (x["date"] <= end_date)]
    .sort_values("date")
)

if filtered.empty or len(filtered) < 2:
    st.warning("Not enough data for the selected filters.")
    st.stop()

# ======================================================
# Séries normalizadas
# ======================================================
price_series = filtered.set_index("date")["close"]
price_norm = normalize_series(price_series)

# ======================================================
# KPIs
# ======================================================
returns = price_series.pct_change().dropna()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Start (Base)", "100")
col2.metric("End", f"{price_norm.iloc[-1]:.2f}")

total_return = price_norm.iloc[-1] - 100
col3.metric("Total Return", f"{total_return:.2f}%")

volatility = returns.std() * np.sqrt(252) * 100
col4.metric("Volatility", f"{volatility:.2f}%")

# ======================================================
# Benchmark - Ibovespa
# ======================================================
st.subheader("Performance (Base 100)")

plot_df = pd.DataFrame({
    ticker: price_norm
})

if "Ibovespa" in benchmarks:
    ibov = (
        df[df["ticker"] == "BOVA11.SA"]
        .loc[lambda x: (x["date"] >= start_date) & (x["date"] <= end_date)]
        .sort_values("date")
        .set_index("date")["close"]
    )

    if len(ibov) >= 2:
        plot_df["Ibovespa"] = normalize_series(ibov)

# ============================
# Plot
# ============================
st.line_chart(plot_df)

