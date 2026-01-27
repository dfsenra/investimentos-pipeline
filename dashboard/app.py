import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Financial Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("data/historical/precos_historicos.csv", parse_dates=["date"])
    return df

df = load_data()
df = df.dropna(subset=["date", "close", "ticker"])

st.title("Financial Asset Explorer")

# Sidebar
st.sidebar.header("Filters")

ticker = st.sidebar.selectbox(
    "Select ticker",
    sorted(df["ticker"].dropna().astype(str).unique())
)

start_date, end_date = st.sidebar.date_input(
    "Select date range",
    [df["date"].min(), df["date"].max()]
)

filtered = df[
    (df["ticker"] == ticker) &
    (df["date"] >= pd.to_datetime(start_date)) &
    (df["date"] <= pd.to_datetime(end_date))
].sort_values("date")

# KPIs
col1, col2, col3, col4, col5 = st.columns(5)

if filtered.empty or len(filtered) < 2:
    st.warning("Not enough data for the selected filters.")
    st.stop()

filtered = filtered.copy()
filtered["close"] = pd.to_numeric(filtered["close"], errors="coerce")
filtered = filtered.dropna(subset=["close"])

price_start = filtered["close"].iloc[0]
price_end = filtered["close"].iloc[-1]

returns = filtered["close"].pct_change().dropna()

col1.metric("Start Price", f"{price_start:.2f}")
col2.metric("End Price", f"{price_end:.2f}")
col3.metric("Return (%)", f"{(price_end/price_start - 1)*100:.2f}%")
col4.metric("Volatility", f"{returns.std()*np.sqrt(252)*100:.2f}%")

drawdown = (filtered["close"] / filtered["close"].cummax() - 1).min()
col5.metric("Max Drawdown", f"{drawdown*100:.2f}%")

# Charts
st.subheader("Price History")
st.line_chart(filtered.set_index("date")["close"])

st.subheader("Volume")
if "volume" in filtered.columns:
    st.subheader("Volume")
    st.bar_chart(filtered.set_index("date")["volume"])

