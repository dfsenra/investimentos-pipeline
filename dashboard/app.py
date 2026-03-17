import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import subprocess
import os
import time
from datetime import date
from sqlalchemy import text
from queries import (
    QUERY_PRECOS, QUERY_GANHOS_DIARIO_CARTEIRA, QUERY_RESUMO_CARTEIRA, QUERY_RESUMO_ATIVOS,
    QUERY_LOG_TRANSACOES, QUERY_RETORNO_TRANSACOES, QUERY_EVOLUCAO_PATRIMONIO, QUERY_ATIVOS_COM_SALDO,
    QUERY_RESULTADO_REALIZADO_TOTAL
)
from dashboard.db import get_engine
from pathlib import Path

pd.set_option('future.no_silent_downcasting', True)

# Formatação do dashboard
st.set_page_config(page_title="Carteira Inteligente", page_icon="💰", layout="wide")

engine = get_engine()

def colorir_rentabilidade(valor):
    if valor is None or pd.isna(valor) or valor == 0:
        return 'color: gray;'
    cor = '#ff4b4b' if valor < 0 else '#00ff00'
    return f'color: {cor}; font-weight: bold;'

def criar_grafico_plotly(df, titulo_y, tickers_formatados={}):
    if df is None or df.empty:
        return None
    fig = go.Figure()
    for col in df.columns:
        nome_exibido = tickers_formatados.get(col, col)
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], mode='lines', name=nome_exibido, connectgaps=True
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

def formatar_tabela_investimentos(df, mapeamento_colunas):
    formatos_mestres = {
        "total_investido": "R$ {:,.2f}",
        "posicao_atual": "R$ {:,.2f}",
        "valor_atual": "R$ {:,.2f}",
        "rentabilidade": "{:.2%}",
        "preco_medio": "R$ {:,.2f}",
        "quantidade_total": "{:,.0f}",
        "id_transacao": "{:,.0f}",
        "quantidade":  "{:,.0f}",
        "preco_transacao": "R$ {:,.2f}",
        "lucro": "R$ {:,.2f}",
        "lucro_percentual": "{:.2%}",
        "lucro_total_realizado": "R$ {:,.2f}",
        "rentabilidade_media_venda": "{:.2%}"
    }
    formatos_colunas = {col: formatos_mestres[col] for col in df.columns if col in formatos_mestres}
    formatado = df.style.format(formatos_colunas, na_rep="N/A")
    colunas_coloriveis = ['rentabilidade', 'lucro', 'lucro_percentual', 'lucro_total_realizado', 'rentabilidade_media_venda']
    colunas_presentes = [col for col in colunas_coloriveis if col in df.columns]

    if colunas_presentes:
        formatado = formatado.map(colorir_rentabilidade, subset=colunas_presentes)
    
    formatado = formatado.hide(axis="index").set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#1d222b'), ('color', 'white')]},
        {'selector': 'td', 'props': [('text-align', 'center'), ('background-color', '#1d222b')]}
    ]).format_index(lambda col: mapeamento_colunas.get(col, col), axis=1)
    
    return formatado.to_html()


# Carregamento de dados

@st.cache_data(ttl=60)
def carrega_dados():
    try:
        df_precos = pd.read_sql(QUERY_PRECOS, engine)
        df_ganhos_diarios = pd.read_sql(QUERY_GANHOS_DIARIO_CARTEIRA, engine)
        if not df_precos.empty: df_precos['data'] = pd.to_datetime(df_precos['data'])
        if not df_ganhos_diarios.empty: df_ganhos_diarios['data'] = pd.to_datetime(df_ganhos_diarios['data'])
        
        df_res_completa = pd.read_sql(QUERY_RESUMO_CARTEIRA, engine).fillna(0)
        df_res = df_res_completa[df_res_completa['valor_atual'] > 0].copy()
        df_atv_res_completa = pd.read_sql(QUERY_RESUMO_ATIVOS, engine).fillna(0)
        df_atv_res = df_atv_res_completa[df_atv_res_completa['posicao_atual'] > 0].copy()
        df_log = pd.read_sql(QUERY_LOG_TRANSACOES, engine).fillna(0)
        df_lucro = pd.read_sql(QUERY_RETORNO_TRANSACOES, engine).fillna(0)
        df_patrimonio = pd.read_sql(QUERY_EVOLUCAO_PATRIMONIO, engine).fillna(0)
        if not df_patrimonio.empty:    
            df_patrimonio['data'] = pd.to_datetime(df_patrimonio['data'])
            df_patrimonio = df_patrimonio.set_index('data')
        
        with engine.connect() as conn:
            ativos_list = pd.read_sql(text(QUERY_ATIVOS_COM_SALDO), conn)["ticker"].tolist()
            indices_list = pd.read_sql(text("SELECT ticker FROM ativos WHERE tipo_ativo = 'indice'"), conn)["ticker"].tolist()
            df_check = pd.read_sql(text("SELECT * FROM transacoes_portfolio LIMIT 1"), conn)
        
        return df_precos, df_ganhos_diarios, df_res, df_atv_res, df_log, df_lucro, df_patrimonio, ativos_list, indices_list, df_check
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return [pd.DataFrame()]*10

df_precos, df_retornos, df_resultados, df_resultados_ativos, df_log, df_lucro, df_patrimonio, ativos, indices, df_check = carrega_dados()


# Menu lateral fixo
def limpar_menu():
    itens_para_limpar = ["ativos_sel", "indices_sel", "chk_carteira", "chk_precos"]
    for itens in itens_para_limpar:
        if itens in st.session_state:
            st.session_state[itens] = [] if "sel" in itens else False
    st.cache_data.clear()

st.sidebar.title("Painel de Controle")
st.sidebar.caption("Clique aqui para atualizar gráficos após inserir novas transações.")

if st.sidebar.button("🔄 Atualizar Cotações", width='stretch'):
    with st.sidebar.status("Sincronizando...", expanded=True) as status:
        arquivo_env = os.environ.copy()
        arquivo_env["PYTHONPATH"] = "/app"
        result = subprocess.run(["python3", "/app/scripts/pipeline_incremental.py"], capture_output=True, text=True, env=arquivo_env)
        if result.returncode == 0:
            status.update(label="Sincronizado!", state="complete")
            limpar_menu()
            st.rerun()
        else: st.error(f"Erro: {result.stderr}")

st.sidebar.markdown("---")
st.sidebar.link_button("✉️ Olá recruiter, vamos conversar!", "mailto:dfsenra@gmail.com")
st.sidebar.markdown("👨‍💻 [Meu Linkedin](https://www.linkedin.com/in/dfsenra/)")
st.sidebar.caption("Versão 2026.1")

# Página principal
st.title("Carteira Inteligente", help = "Esta aplicação gera dados para suportar as suas decisões, mas não fornece recomendações de investimentos.")
st.caption("Cotações atualizadas em D-1 (ontem). Fonte: Yahoo Finance.")

aba_tutorial, aba_dash, aba_reg, aba_log = st.tabs(["Como usar esta App", "Dashboard de Performance", "Registrar Operações", "Log de Operações"])

with aba_tutorial:

    caminho_tutorial_app = Path(__file__).parent / "tutorial_da_app.md"

    def importar_tutorial_app(caminho):
        conteudo = caminho.read_text(encoding="utf-8")
        st.markdown(conteudo, unsafe_allow_html=True)
    
    importar_tutorial_app(caminho_tutorial_app)

with aba_dash:

    if df_check.empty:
        st.info("Sua carteira está vazia. Vá em 'Registrar Operações' para começar!")
    else:
        st.markdown("##### Performance e Retornos:")
        col_performance, col_retorno = st.columns(2)
        with col_performance:
            with st.expander("Performance da Carteira"):
                st.caption("Posição consolidada da carteira ativa.")
                map_cols = {"total_investido": "Total Investido", "valor_atual": "Posição Atual", "rentabilidade": "Rentabilidade", "preco_medio": "Preço Médio", "quantidade_total": "Qtd", "posicao_atual": "Posição Atual", "ticker": "Ticker"}
                
                st.markdown('<h3 style="text-align: center;">Performance Geral</h3>', unsafe_allow_html=True)
                res_geral_html = formatar_tabela_investimentos(df_resultados, map_cols)
                st.markdown(f'<div style="display: flex; justify-content: center;">{res_geral_html}</div>', unsafe_allow_html=True)
    
                with st.expander("Ver performance por ativo"):
                    st.markdown('<h3 style="text-align: center;">Performance por Ativo</h3>', unsafe_allow_html=True)
                    res_atv_html = formatar_tabela_investimentos(df_resultados_ativos, map_cols)
                    st.markdown(f'<div style="display: flex; justify-content: center;">{res_atv_html}</div>', unsafe_allow_html=True)
        
        with col_retorno:
            with st.expander("Retornos Realizados"):
                st.caption("Retornos consolidados em operações de venda já encerradas.")
                try:
                    df_lucro_realizado = pd.read_sql(QUERY_RESULTADO_REALIZADO_TOTAL, engine)
                            
                    if not df_lucro_realizado.empty:
                        total_realizado = df_lucro_realizado['lucro_total_realizado'].sum()
                        map_cols_log = {
                            "ticker": "Ticker", 
                            "lucro_total_realizado": "Lucro Total Realizado", 
                            "rentabilidade_media_venda": "Rentabilidade Média" 
                        }
                        
                        st.metric("Saldo Realizado Acumulado", f"R$ {total_realizado:,.2f}")            
                        with st.expander("Ver retornos detalhados por ativo"):        

                            log_lucros_html = formatar_tabela_investimentos(df_lucro_realizado, map_cols_log)
                            st.markdown(f'<div style="display: flex; justify-content: center;">{log_lucros_html}</div>', unsafe_allow_html=True)

                    else:
                        st.info("Ainda não há retornos realizados (vendas) registrados.")
                except:
                    pass

        st.markdown("---")

        st.markdown("##### Gráficos:")
        col_ativos, col_indices = st.columns(2)
        with col_ativos:
            ativos_selecionados = st.multiselect(
                "Ativos da sua carteira",
                options=ativos,
                key = "ativos_sel")

        tickers_formatados = {"^GSPC": "S&P 500", "^BVSP": "IBOVESPA"}
        with col_indices:
            indices_selecionados = st.multiselect(
            "Índices de mercado",
            options=indices,
            format_func=lambda x: tickers_formatados.get(x, x),
            default=[]
            )

        st.markdown("###### Recursos extras:")
        
        patrimonio_checkbox = st.checkbox("Incluir Evolução Patrimonial (R$)", value=False)
        precos_checkbox = st.checkbox("Incluir gráfico com preços (R$)", value=False)

        if patrimonio_checkbox and not df_patrimonio.empty:
            st.markdown("#### Evolução Patrimonial (R$)")
            fig_patrimonio = criar_grafico_plotly(df_patrimonio, "Patrimônio Total (R$)", {"patrimonio_total": "Total na Carteira"})
            
            if fig_patrimonio:
                st.plotly_chart(fig_patrimonio, width='stretch')
            st.markdown("---")

        if not ativos_selecionados and not indices_selecionados and not patrimonio_checkbox:
            if precos_checkbox:
                st.warning("Estamos ansiosos para te mostrar os gráficos! Mas antes preciso que você selecione um ativo ou 'Incluir Evolução Patrimonial' 😬")

            else:
                st.info("Selecione ao menos um ativo, índice ou 'Incluir Evolução Patrimonial' nas opções acima.")
        
        
        elif precos_checkbox and not ativos_selecionados and indices_selecionados:

            chart_df_retorno_ind = pd.DataFrame()

            for i in indices_selecionados:
                if not df_retornos.empty:
                    mask_i = df_retornos["ticker"] == i
                    if mask_i.any():
                        chart_df_retorno_ind[i] = df_retornos[mask_i].set_index("data")["retorno_diario"]

            if not chart_df_retorno_ind.empty:
                chart_df_retorno_ind = chart_df_retorno_ind.sort_index().fillna(0)
                df_ind_normalizado = (1 + chart_df_retorno_ind).cumprod() * 100

                st.markdown("### Rentabilidade acumulada")
                cols = st.columns(len(chart_df_retorno_ind.columns))
                for col_ui, col_name in zip(cols, chart_df_retorno_ind.columns):
                    rent_final = (df_ind_normalizado[col_name].iloc[-1] / 100) - 1
                    display_name = tickers_formatados.get(col_name, col_name)
                    color = '#00ff00' if rent_final >= 0 else '#ff4b4b'
                    with col_ui:
                        st.markdown(f"""
                            <div style="line-height: 1.2;">
                                <p style="color: #808495; font-size: 0.9rem; margin-bottom: 2px;">{display_name}</p>
                                <p style="font-size: 1.5rem; font-weight: bold; margin-top: 0; color: {color};">{rent_final:.2%}</p>
                            </div>
                        """, unsafe_allow_html=True)     

                st.chat_message("assistant", avatar="❗").write("Os **Índices** não possuem gráfico de preços (R$) aqui, apenas performance.")
                st.markdown("#### Performance Normalizada (Base 100)")
                st.plotly_chart(criar_grafico_plotly(df_ind_normalizado, "Performance", tickers_formatados), width='stretch')
        
        else:

            chart_df_retorno = pd.DataFrame()
            chart_df_precos = pd.DataFrame()

            for r in ativos_selecionados + indices_selecionados:
                if not df_retornos.empty:
                    mask = df_retornos["ticker"] == r
                    if mask.any():
                        chart_df_retorno[r] = df_retornos[mask].set_index("data")["retorno_diario"]
                
            for p in ativos_selecionados:    
                if precos_checkbox and not df_precos.empty:
                    mask_r = (df_precos["ticker"] == p)
                    if mask_r.any():
                        chart_df_precos[p] = df_precos[mask_r].set_index("data")["preco_fechamento"]

            if not chart_df_retorno.empty:
                chart_df_retorno = chart_df_retorno.sort_index().fillna(0)
                df_normalizado = (1 + chart_df_retorno).cumprod() * 100

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

                if precos_checkbox and not chart_df_precos.empty:
                    st.markdown("#### Evolução de Preços (R$)")
                    st.plotly_chart(criar_grafico_plotly(chart_df_precos.sort_index().ffill(), "Preço (R$)", tickers_formatados), width='stretch')

                st.markdown("#### Performance Normalizada (Base 100)")
                st.plotly_chart(criar_grafico_plotly(df_normalizado, "Performance", tickers_formatados), width='stretch')

with aba_reg:

    st.subheader("Cadastrar Nova Transação")
    
    
    with engine.connect() as conn:
        df_saldos = pd.read_sql("SELECT ticker, quantidade_total FROM view_posicao_carteira", conn)
        saldos_dict = dict(zip(df_saldos['ticker'], df_saldos['quantidade_total']))

    with st.form("form_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t_ticker = c1.text_input("Ticker (ex: PETR4.SA)").upper().strip()
        t_data = c1.date_input("Data")
        t_tipo = c2.selectbox("Tipo", ["Compra", "Venda"])
        t_qtd = c2.number_input("Quantidade", min_value=0, step=1, value=0)

        t_preco = st.number_input("Preço Unitário (R$)", min_value=0.0)
        
        if st.form_submit_button("Salvar Transação"):
            
            if t_preco <= 0 or t_qtd <= 0:
                st.error("❌ Preço e Quantidade devem ser maiores que zero.")
            elif not t_ticker:
                st.error("❌ Digite um Ticker válido.")
            else:
                saldo_atual = saldos_dict.get(t_ticker, 0.0)
                if t_tipo == "Venda" and t_qtd > saldo_atual:
                    st.error(f"❌ Saldo insuficiente ({saldo_atual:.0f} cotas).")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO ativos (ticker, tipo_ativo) VALUES (:t, 'ativo') ON CONFLICT DO NOTHING"), {"t": t_ticker})
                        a_id = conn.execute(text("SELECT id_ativo FROM ativos WHERE ticker = :t"), {"t": t_ticker}).scalar()
                        
                        conn.execute(text("""
                            INSERT INTO transacoes_portfolio (id_ativo, data_transacao, quantidade, preco_transacao, tipo_transacao) 
                            VALUES (:aid, :d, :q, :p, :tipo)
                        """), {"aid": a_id, "d": t_data, "q": t_qtd, "p": t_preco, "tipo": t_tipo})
                    
                    st.success(f"{t_tipo} de {t_ticker} registrada! Clique em '🔄 Atualizar Cotações' para atualizar os gráficos!")
                    time.sleep(6)
                    st.cache_data.clear()
                    st.rerun()

with aba_log:

    st.subheader("🗑️ Gerenciar Histórico")
    st.caption("Caso tenha inserido uma operação com dados incorretos, não se preocupe, use essa seção para remoções. O Preço Médio será recalculado automaticamente.")

    if not df_log.empty:
        opcoes_delete = df_log.sort_values("id_transacao", ascending=False)
        transacao_para_deletar = st.selectbox(
            "Escolha a transação que deseja excluir:",
            options=opcoes_delete["id_transacao"].tolist(),
            format_func=lambda x: f"ID: {x} | {opcoes_delete[opcoes_delete['id_transacao']==x]['ticker'].values[0]} | {opcoes_delete[opcoes_delete['id_transacao']==x]['tipo_transacao'].values[0]} | {opcoes_delete[opcoes_delete['id_transacao']==x]['data_transacao'].values[0]}"
        )

        if st.button("⚠️ Deletar Transação Selecionada", type="primary"):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("DELETE FROM transacoes_portfolio WHERE id_transacao = :tid"),
                        {"tid": transacao_para_deletar}
                    )
                st.success(f"Transação {transacao_para_deletar} removida com sucesso!")
                st.cache_data.clear()       # limpar o cache eliminou o bug do preço médio não atualizar
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao deletar: {e}")
    else:
        st.info("Nenhuma transação encontrada para deletar.")

    st.markdown("---")

    st.subheader("Histórico Geral de Transações")
    st.caption("Consulte todas as transações realizadas.")
    with st.expander("Histórico Geral de Transações", expanded=False):
        map_cols_log = {
            "id_transacao": "# Transação", 
            "ticker": "Ticker", 
            "quantidade": "Quantidade", 
            "preco_transacao": "Preço executado", 
            "data_transacao": "Data", 
            "tipo_transacao": "Tipo", 
            "lucro": "Retorno (R$)", 
            "lucro_percentual": "Retorno (%)"
            }
        st.markdown('<h3 style="text-align: center;">Registro de Operações</h3>', unsafe_allow_html=True)
        
        df_log_final = pd.concat([df_log, df_lucro], axis=1)
        df_log_final = df_log_final.loc[:, ~df_log_final.columns.duplicated()].copy()
        df_log_final = df_log_final.reset_index(drop=True)
        log_transacoes_html = formatar_tabela_investimentos(df_log_final, map_cols_log)
        st.markdown(f'<div style="display: flex; justify-content: center;">{log_transacoes_html}</div>', unsafe_allow_html=True)


    
