import streamlit as st
import pandas as pd
from queries import PRICES_QUERY, RETURNS_QUERY, CARTEIRA_RESUMO_QUERY
from dashboard.db import get_engine

st.set_page_config(
    page_title="AI Portfolio",
    page_icon="💰",
    layout="wide"
)

engine = get_engine()

st.title("AI Portfolio - Invista com inteligência")
st.caption("Este modelo não gera recomendações de investimentos. Ele fornece dados para você tomar as melhores decisões para a sua carteira.")

# =============================
# Dados
# =============================
df_prices = pd.read_sql(PRICES_QUERY, engine)
df_returns = pd.read_sql(RETURNS_QUERY, engine)

# =============================
# Sidebar
# =============================
st.sidebar.title("Aqui você encontra:")

st.sidebar.caption("⏺ Benchmark com índices do mercado")
st.sidebar.caption("⏺ Análise preditiva")
st.sidebar.caption("⏺ Performance da sua carteira")

st.sidebar.markdown("---")

ativos = sorted(df_prices["ticker"].unique())

ativos_selecionados = st.sidebar.multiselect(
    "Ativos da sua carteira",
    options=ativos,
    help="Estes são os ativos que você registrou no tickers.csv",
    default=[]
)

indices_selecionados = st.sidebar.multiselect(
    "Índices de mercado",
    options=["^GSPC"],
    help="GSPC = S&P500",  # CDI e IBOV entram depois
    default=[]
)

st.sidebar.markdown("---")
st.sidebar.link_button("✉️ Olá recruiter, vamos conversar!", "mailto:dfsenra@gmail.com")
st.sidebar.markdown("👨‍💻 [Meu Linkedin](https://www.linkedin.com/in/dfsenra/)")

chart_df = pd.DataFrame()

# =============================
# Carteira (sempre presente)
# =============================
carteira = (
    df_returns.groupby("data")["retorno_diario"]
    .mean()
    .dropna()
)

chart_df["Carteira"] = carteira

# =============================
# Ativos selecionados
# =============================
for ticker in ativos_selecionados:
    serie = (
        df_returns[df_returns["ticker"] == ticker]
        .set_index("data")["retorno_diario"]
        .dropna()
    )
    chart_df[ticker] = serie

# =============================
# Índices selecionados
# =============================
for idx in indices_selecionados:                       # Será travado apenas opção por vez devido a unidades diferentes (Pontos/R$/Rentabilidade)
    serie = (
        df_returns[df_returns["ticker"] == idx]
        .set_index("data")["retorno_diario"]
        .dropna()
    )
    chart_df[idx] = serie

chart_df = chart_df.sort_index()

# =============================
# Métricas no topo
# =============================
if chart_df.empty or len(chart_df.columns) == 0:
    st.info("Selecione ao menos um ativo ou índice.")  # isso era uma segurança que não precisa mais, porém deixei no código
    st.stop()

st.markdown("### Rentabilidade acumulada")             # Todos os cálculos de rentabilidade são feitos em cima do preço (R$)

cols = st.columns(len(chart_df.columns))

for col_ui, col in zip(cols, chart_df.columns):
    rent = (1 + chart_df[col].dropna()).prod() - 1
    col_ui.metric(col, f"{rent:.2%}")

# =============================
# Normalização para gráfico
# =============================
normalized_df = pd.DataFrame(index=chart_df.index)          # Normalizei os dados para reduzir ruídos, ficar mais legível
                                                            # Todos os preços estão na base 100
for col in chart_df.columns:
    s = chart_df[col].dropna()

    if len(s) == 0:
        continue

    base = (1 + s).cumprod()
    base = base / base.iloc[0] * 100

    normalized_df[col] = base

st.line_chart(normalized_df)

