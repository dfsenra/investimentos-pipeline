# Antes eu havia colocado cálculos executados pelo dashboard o que gerou problemas
# Todos os cálculos são feitos pelas views e as queries só fazem o filtro que são chamadas pelo dashboard

# =========================
# Preços históricos
# =========================

PRICES_QUERY = """
SELECT
    ticker,
    data,
    close_price
FROM vw_asset_returns
ORDER BY data
"""


# =========================
# Retornos percentuais
# =========================

RETURNS_QUERY = """
SELECT
    ticker,
    data,
    retorno_diario
FROM vw_asset_returns
WHERE retorno_diario IS NOT NULL
ORDER BY data
"""


# =========================
# Carteira (resumo geral)
# =========================

CARTEIRA_RESUMO_QUERY = """
SELECT *
FROM vw_carteira_resumo
"""


# ============================
# Carteira (resumo por ativos)
# ============================

CARTEIRA_RESUMO_ATIVOS_QUERY = """
SELECT
    ticker,
    quantidade_total,
    preco_medio,
    total_investido,
    posicao_atual,
    rentabilidade
FROM vw_portfolio_status
ORDER BY rentabilidade DESC
"""

# ==================================
# Ativos com saldo ativo na carteira
# ==================================
ATIVOS_COM_SALDO_QUERY = """
SELECT DISTINCT ticker 
FROM vw_portfolio_status 
WHERE quantidade_total > 0
"""

# ============================
# Consulta log de transações
# ============================
CONSULTA_LOG_QUERY = """
SELECT
    transaction_id,
    ticker,
    quantidade,
    preco_transacao,
    data_transacao,
    tipo_transacao
FROM vw_portfolio_transactions
ORDER BY transaction_id DESC
"""

# ============================
# Consulta lucro sobre vendas
# ============================
CONSULTA_LUCRO_QUERY = """
SELECT 
    t.ticker,
    t.tipo_transacao,
    CASE 
        WHEN t.tipo_transacao = 'Venda' THEN (t.preco_transacao - c.preco_medio_momento_anterior) * t.quantidade 
        ELSE NULL 
    END AS lucro,
    CASE 
        WHEN t.tipo_transacao = 'Venda' THEN (t.preco_transacao - c.preco_medio_momento_anterior) / NULLIF(c.preco_medio_momento_anterior, 0) 
        ELSE NULL
    END AS lucro_percentual
FROM (
    -- Subquery para pegar o preço médio que existia ANTES da transação atual
    SELECT 
        *,
        LAG(preco_medio_momento) OVER (PARTITION BY asset_id ORDER BY transaction_id) as preco_medio_momento_anterior
    FROM vw_calculo_medio_recursivo
) c
JOIN vw_portfolio_transactions t ON t.transaction_id = c.transaction_id
ORDER BY t.transaction_id DESC;
"""

# ===============================
# Consulta evolução do patrimônio
# ===============================
EVOLUCAO_PATRIMONIO_QUERY = "SELECT * FROM vw_evolucao_patrimonio"
    
    
# ===============================
# Consulta Lucro Realizado
# ===============================
LUCRO_REALIZADO_TOTAL_QUERY = """
SELECT 
    ticker,
    SUM(lucro) as lucro_total_realizado,
    AVG(lucro_percentual) as rentabilidade_media_venda
FROM (
    SELECT 
        t.ticker,
        (t.preco_transacao - c.preco_medio_momento_anterior) * t.quantidade as lucro,
        (t.preco_transacao - c.preco_medio_momento_anterior) / NULLIF(c.preco_medio_momento_anterior, 0) as lucro_percentual
    FROM (
        SELECT *, LAG(preco_medio_momento) OVER (PARTITION BY asset_id ORDER BY transaction_id) as preco_medio_momento_anterior
        FROM vw_calculo_medio_recursivo
    ) c
    JOIN vw_portfolio_transactions t ON t.transaction_id = c.transaction_id
    WHERE t.tipo_transacao = 'Venda'
) sub
GROUP BY ticker
ORDER BY lucro_total_realizado DESC
"""