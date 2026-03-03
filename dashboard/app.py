import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import subprocess
import os
import time
from sqlalchemy import text
from queries import (
    PRICES_QUERY, RETURNS_QUERY, CARTEIRA_RESUMO_QUERY, CARTEIRA_RESUMO_ATIVOS_QUERY,
    CONSULTA_LOG_QUERY, CONSULTA_LUCRO_QUERY, EVOLUCAO_PATRIMONIO_QUERY, ATIVOS_COM_SALDO_QUERY,
    LUCRO_REALIZADO_TOTAL_QUERY
)
from dashboard.db import get_engine

# 1. Configuração da página
st.set_page_config(page_title="AI Portfolio", page_icon="💰", layout="wide")

engine = get_engine()

# ======================================================
# Funções auxiliares e Estilização
# ======================================================

def colorir_rentabilidade(valor):
    if valor is None or pd.isna(valor) or valor == 0:
        return 'color: gray;'
    color = '#ff4b4b' if valor < 0 else '#00ff00'
    return f'color: {color}; font-weight: bold;'

def criar_grafico_plotly(df, titulo_y, tickers_formatados={}):
    if df is None or df.empty:
        return None
    fig = go.Figure()
    for col in df.columns:
        display_name = tickers_formatados.get(col, col)
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], mode='lines', name=display_name, connectgaps=True
        ))
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Data"),
        yaxis=dict(title=titulo_y)
    )
    return fig

def estilizar_tabela_investimentos(df, mapeamento_colunas):
    formatos_mestres = {
        "total_investido": "R$ {:,.2f}",
        "posicao_atual": "R$ {:,.2f}",
        "valor_atual": "R$ {:,.2f}",
        "rentabilidade": "{:.2%}",
        "preco_medio": "R$ {:,.2f}",
        "quantidade_total": "{:,.0f}",
        "transaction_id": "{:,.0f}",
        "quantidade":  "{:,.0f}",
        "preco_transacao": "R$ {:,.2f}",
        "lucro": "R$ {:,.2f}",
        "lucro_percentual": "{:.2%}",
        "lucro_total_realizado": "R$ {:,.2f}",
        "rentabilidade_media_venda": "{:.2%}"
    }
    formatos_colunas = {col: formatos_mestres[col] for col in df.columns if col in formatos_mestres}
    styled = df.style.format(formatos_colunas, na_rep="N/A")
    colunas_coloriveis = ['rentabilidade', 'lucro', 'lucro_percentual', 'lucro_total_realizado', 'rentabilidade_media_venda']
    colunas_presentes = [col for col in colunas_coloriveis if col in df.columns]

    if colunas_presentes:
        styled = styled.map(colorir_rentabilidade, subset=colunas_presentes)
    
    styled = styled.hide(axis="index").set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#1d222b'), ('color', 'white')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('background-color', '#1d222b')]}
    ]).format_index(lambda col: mapeamento_colunas.get(col, col), axis=1)
    
    return styled.to_html()

# ======================================================
# 2. Carregamento de Dados
# ======================================================

@st.cache_data(ttl=60)
def load_data():
    try:
        df_p = pd.read_sql(PRICES_QUERY, engine)
        df_r = pd.read_sql(RETURNS_QUERY, engine)
        if not df_p.empty: df_p['data'] = pd.to_datetime(df_p['data'])
        if not df_r.empty: df_r['data'] = pd.to_datetime(df_r['data'])
        
        df_res_completa = pd.read_sql(CARTEIRA_RESUMO_QUERY, engine).fillna(0)
        df_res = df_res_completa[df_res_completa['valor_atual'] > 0].copy()
        df_atv_res_completa = pd.read_sql(CARTEIRA_RESUMO_ATIVOS_QUERY, engine).fillna(0)
        df_atv_res = df_atv_res_completa[df_atv_res_completa['posicao_atual'] > 0].copy()
        df_log = pd.read_sql(CONSULTA_LOG_QUERY, engine).fillna(0)
        df_lucro = pd.read_sql(CONSULTA_LUCRO_QUERY, engine).fillna(0)
        df_patrimonio = pd.read_sql(EVOLUCAO_PATRIMONIO_QUERY, engine).fillna(0)
        if not df_patrimonio.empty:    
            df_patrimonio['data'] = pd.to_datetime(df_patrimonio['data'])
            df_patrimonio = df_patrimonio.set_index('data')
        
        with engine.connect() as conn:
            ativos_list = pd.read_sql(text(ATIVOS_COM_SALDO_QUERY), conn)["ticker"].tolist()
            indices_list = pd.read_sql(text("SELECT ticker FROM assets WHERE asset_type = 'indice'"), conn)["ticker"].tolist()
            df_check = pd.read_sql(text("SELECT * FROM portfolio_transactions LIMIT 1"), conn)
        
        return df_p, df_r, df_res, df_atv_res, df_log, df_lucro, df_patrimonio, ativos_list, indices_list, df_check
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return [pd.DataFrame()]*10

df_prices, df_returns, df_resultados, df_resultados_ativos, df_log, df_lucro, df_patrimonio, ativos, indices, df_check = load_data()

# ======================================================
# 3. Sidebar
# ======================================================

def reset_filtros():
    """Função para limpar os menus da sidebar"""
    keys_para_limpar = ["ativos_sel", "indices_sel", "chk_carteira", "chk_precos"]
    for key in keys_para_limpar:
        if key in st.session_state:
            st.session_state[key] = [] if "sel" in key else False
    st.cache_data.clear()

st.sidebar.title("⚙️ Painel de Controle")

if st.sidebar.button("🔄 Atualizar Cotações", width='stretch'):
    with st.sidebar.status("Sincronizando...", expanded=True) as status:
        my_env = os.environ.copy()
        my_env["PYTHONPATH"] = "/app"
        result = subprocess.run(["python3", "/app/scripts/backfill_historico.py"], capture_output=True, text=True, env=my_env)
        if result.returncode == 0:
            status.update(label="✅ Sincronizado!", state="complete")
            reset_filtros()
            st.rerun()
        else: st.error(f"Erro: {result.stderr}")

st.sidebar.markdown("---")
ativos_selecionados = st.sidebar.multiselect("Ativos da sua carteira", options=ativos, key = "ativos_sel")

tickers_formatados = {"^GSPC": "S&P 500", "^BVSP": "IBOVESPA"}
indices_selecionados = st.sidebar.multiselect(
    "Índices de mercado", options=indices, format_func=lambda x: tickers_formatados.get(x, x), default=[]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Recursos extras:")
patrimonio_checkbox = st.sidebar.checkbox("Incluir Evolução Patrimonial (R$)", value=False)
precos_checkbox = st.sidebar.checkbox("Incluir gráfico com preços (R$)", value=False)

st.sidebar.markdown("---")
st.sidebar.link_button("✉️ Olá recruiter, vamos conversar!", "mailto:dfsenra@gmail.com")
st.sidebar.markdown("👨‍💻 [Meu Linkedin](https://www.linkedin.com/in/dfsenra/)")

# ======================================================
# 4. Interface Principal
# ======================================================

st.title("💰 AI Portfolio Manager")

tab_dash, tab_reg, tab_log = st.tabs(["📊 Dashboard de Performance", "➕ Registrar Operações", "Log de Operações"])

with tab_dash:
    if df_check.empty:
        st.info("👋 Sua carteira está vazia. Vá em 'Registrar Operações' para começar!")
    else:

        if patrimonio_checkbox and not df_patrimonio.empty:
            st.markdown("#### Evolução Patrimonial (R$)")
            fig_patrimonio = criar_grafico_plotly(df_patrimonio, "Patrimônio Total (R$)", {"patrimonio_total": "Total na Carteira"})
            
            if fig_patrimonio:
                st.plotly_chart(fig_patrimonio, width='stretch')
            st.markdown("---")

        # 1. Tabelas de Resultados CENTRALIZADAS
        with st.expander("Resultados da Carteira", expanded=True):
            map_cols = {"total_investido": "Total Investido", "valor_atual": "Posição Atual", "rentabilidade": "Rentabilidade", "preco_medio": "Preço Médio", "quantidade_total": "Qtd", "posicao_atual": "Posição Atual", "ticker": "Ticker"}
            
            st.markdown('<h3 style="text-align: center;">Resumo Geral</h3>', unsafe_allow_html=True)
            res_geral_html = estilizar_tabela_investimentos(df_resultados, map_cols)
            st.markdown(f'<div style="display: flex; justify-content: center;">{res_geral_html}</div>', unsafe_allow_html=True)
            
            st.markdown('<h3 style="text-align: center;">Por Ativo</h3>', unsafe_allow_html=True)
            res_atv_html = estilizar_tabela_investimentos(df_resultados_ativos, map_cols)
            st.markdown(f'<div style="display: flex; justify-content: center;">{res_atv_html}</div>', unsafe_allow_html=True)

        # 2. Lógica de Filtros e Avisos
        if not ativos_selecionados and not indices_selecionados and not patrimonio_checkbox:
            if precos_checkbox:
                st.warning("Estamos ansiosos para te mostrar os preços! Mas antes preciso que você selecione um ativo ou 'Incluir Carteira' 😬")
            else:
                st.info("Selecione ao menos um ativo, índice ou 'Incluir Carteira' na barra lateral.")
        else:
            if precos_checkbox and not ativos_selecionados and not patrimonio_checkbox and indices_selecionados:
                st.chat_message("assistant", avatar="❗").write("Os **Índices** não possuem gráfico de preços (R$) aqui, apenas performance.")

            # 3. Processamento dos Gráficos
            chart_df_retorno = pd.DataFrame()
            chart_df_precos = pd.DataFrame()
            chart_df_carteira = pd.DataFrame()

            for t in ativos_selecionados + indices_selecionados:
                if not df_returns.empty:
                    mask = df_returns["ticker"] == t
                    if mask.any():
                        chart_df_retorno[t] = df_returns[mask].set_index("data")["retorno_diario"]
                
                if precos_checkbox and not df_prices.empty:
                    mask_p = (df_prices["ticker"] == t)
                    if mask_p.any():
                        chart_df_precos[t] = df_prices[mask_p].set_index("data")["close_price"]

            if not chart_df_retorno.empty:
                chart_df_retorno = chart_df_retorno.sort_index().fillna(0)
                df_normalizado = (1 + chart_df_retorno).cumprod() * 100

                # 4. Métricas no topo
                st.markdown("### Rentabilidade acumulada")
                cols = st.columns(len(chart_df_retorno.columns))
                for col_ui, col_name in zip(cols, chart_df_retorno.columns):
                    rent_final = (df_normalizado[col_name].iloc[-1] / 100) - 1
                    display_name = tickers_formatados.get(col_name, col_name)
                    color = '#00ff00' if rent_final >= 0 else '#ff4b4b'
                    with col_ui:
                        st.markdown(f"""
                            <div style="line-height: 1.2;">
                                <p style="color: #808495; font-size: 0.9rem; margin-bottom: 2px;">{display_name}</p>
                                <p style="font-size: 1.5rem; font-weight: bold; margin-top: 0; color: {color};">{rent_final:.2%}</p>
                            </div>
                        """, unsafe_allow_html=True)

                # 5. Renderização dos Gráficos
                if precos_checkbox and not chart_df_precos.empty:
                    st.markdown("#### Evolução de Preços (R$)")
                    st.plotly_chart(criar_grafico_plotly(chart_df_precos.sort_index().ffill(), "Preço (R$)", tickers_formatados), width='stretch')

                st.markdown("#### Performance Normalizada (Base 100)")
                st.plotly_chart(criar_grafico_plotly(df_normalizado, "Performance", tickers_formatados), width='stretch')

with tab_reg:
    st.subheader("📝 Cadastrar Nova Transação")
    
    # Buscamos o saldo atual de todos os ativos para validar a venda
    with engine.connect() as conn:
        df_saldos = pd.read_sql("SELECT ticker, quantidade_total FROM vw_portfolio_positions", conn)
        saldos_dict = dict(zip(df_saldos['ticker'], df_saldos['quantidade_total']))

    with st.form("form_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t_ticker = c1.text_input("Ticker (ex: PETR4.SA)").upper().strip()
        t_data = c1.date_input("Data")
        t_tipo = c2.selectbox("Tipo", ["Compra", "Venda"])
        t_qtd = c2.number_input("Quantidade", min_value=0.0)
        t_preco = st.number_input("Preço Unitário (R$)", min_value=0.0)
        
        if st.form_submit_button("🚀 Salvar Transação"):
            # 1. Validações de entrada
            if t_preco <= 0 or t_qtd <= 0:
                st.error("❌ Preço e Quantidade devem ser maiores que zero.")
            elif not t_ticker:
                st.error("❌ Digite um Ticker válido.")
            else:
                # 2. Lógica de inserção (como você já tinha, mas com a segurança extra)
                saldo_atual = saldos_dict.get(t_ticker, 0.0)
                if t_tipo == "Venda" and t_qtd > saldo_atual:
                    st.error(f"❌ Saldo insuficiente ({saldo_atual:.0f} cotas).")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO assets (ticker, asset_type) VALUES (:t, 'ativo') ON CONFLICT DO NOTHING"), {"t": t_ticker})
                        a_id = conn.execute(text("SELECT asset_id FROM assets WHERE ticker = :t"), {"t": t_ticker}).scalar()
                        
                        conn.execute(text("""
                            INSERT INTO portfolio_transactions (asset_id, data_transacao, quantidade, preco_transacao, tipo_transacao) 
                            VALUES (:aid, :d, :q, :p, :tipo)
                        """), {"aid": a_id, "d": t_data, "q": t_qtd, "p": t_preco, "tipo": t_tipo})
                    
                    st.success(f"✅ {t_tipo} de {t_ticker} registrada! Clique em '🔄 Atualizar Cotações' para recalcular a sua carteira!")
                    time.sleep(5)
                    st.cache_data.clear()
                    st.rerun()

with tab_log:

    st.subheader("💰 Resumo de Lucro Realizado")
    st.caption("Ganhos consolidados em operações de venda já encerradas.")

    # Carregar dados de lucro realizado (precisa adicionar na função load_data)
    # Aqui assumindo que df_lucro_total vem do load_data()
    try:
        df_lucro_realizado = pd.read_sql(LUCRO_REALIZADO_TOTAL_QUERY, engine)
        
        if not df_lucro_realizado.empty:
            total_realizado = df_lucro_realizado['lucro_total_realizado'].sum()
            map_cols_log = {
                "ticker": "Ticker", 
                "lucro_total_realizado": "Lucro Total Realizado", 
                "rentabilidade_media_venda": "Rentabilidade Média" 
            }
            # Card de destaque
            st.metric("Lucro Realizado Acumulado", f"R$ {total_realizado:,.2f}")
            
            with st.expander("Ver lucro detalhado por ativo"):
                # Formatação simples para a tabela de lucro realizado
                log_lucros_html = estilizar_tabela_investimentos(df_lucro_realizado, map_cols_log)
                st.markdown(f'<div style="display: flex; justify-content: center;">{log_lucros_html}</div>', unsafe_allow_html=True)

        else:
            st.info("Ainda não há lucros realizados (vendas) registrados.")
    except:
        pass

    st.markdown("---")

    st.subheader("🗑️ Gerenciar Histórico")
    st.caption("Caso tenha inserido uma operação com dados incorretos, não se preocupe, use essa seção para remoções. O Preço Médio será recalculado automaticamente.")

    # Criamos um selectbox para escolher o ID da transação
    if not df_log.empty:
        # Preparar lista de opções formatada: "ID - TICKER - TIPO - DATA"
        opcoes_delete = df_log.sort_values("transaction_id", ascending=False)
        transacao_para_deletar = st.selectbox(
            "Escolha a transação que deseja excluir:",
            options=opcoes_delete["transaction_id"].tolist(),
            format_func=lambda x: f"ID: {x} | {opcoes_delete[opcoes_delete['transaction_id']==x]['ticker'].values[0]} | {opcoes_delete[opcoes_delete['transaction_id']==x]['tipo_transacao'].values[0]} | {opcoes_delete[opcoes_delete['transaction_id']==x]['data_transacao'].values[0]}"
        )

        if st.button("⚠️ Deletar Transação Selecionada", type="primary"):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("DELETE FROM portfolio_transactions WHERE transaction_id = :tid"),
                        {"tid": transacao_para_deletar}
                    )
                st.success(f"✅ Transação {transacao_para_deletar} removida com sucesso!")
                st.cache_data.clear() # Limpa o cache para o PM atualizar
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao deletar: {e}")
    else:
        st.info("Nenhuma transação encontrada para deletar.")

    st.markdown("---")

    st.subheader("📜 Histórico Geral de Transações")
    st.caption("Consulte todas as transações realizadas.")
    with st.expander("Histórico Geral de Transações", expanded=False):
        map_cols_log = {
            "transaction_id": "# Transação", 
            "ticker": "Ticker", 
            "quantidade": "Quantidade", 
            "preco_transacao": "Preço executado", 
            "data_transacao": "Data", 
            "tipo_transacao": "Tipo", 
            "lucro": "Retorno (R$)", 
            "lucro_percentual": "Retorno (%)"
            }
        st.markdown('<h3 style="text-align: center;">Registro de Operações</h3>', unsafe_allow_html=True)
        
        # 1. Concatenar
        df_log_final = pd.concat([df_log, df_lucro], axis=1)
        
        # 2. REMOVER COLUNAS DUPLICADAS (O "Pulo do Gato")
        # Isso mantém apenas a primeira ocorrência de colunas com mesmo nome
        df_log_final = df_log_final.loc[:, ~df_log_final.columns.duplicated()].copy()
        
        # 3. Resetar o índice para garantir unicidade total
        df_log_final = df_log_final.reset_index(drop=True)
        
        # 4. Chamar a estilização (agora sem erro de KeyError)
        log_transacoes_html = estilizar_tabela_investimentos(df_log_final, map_cols_log)
        st.markdown(f'<div style="display: flex; justify-content: center;">{log_transacoes_html}</div>', unsafe_allow_html=True)


    
