
QUERY_PRECOS = """
SELECT
    ticker,
    data,
    preco_fechamento
FROM view_ganhos_carteira
ORDER BY data
"""


QUERY_GANHOS_DIARIO_CARTEIRA = """
SELECT
    ticker,
    data,
    retorno_diario
FROM view_ganhos_carteira
WHERE retorno_diario IS NOT NULL
ORDER BY data
"""


QUERY_RESUMO_CARTEIRA = """
SELECT *
FROM view_resumo_carteira
"""


QUERY_RESUMO_ATIVOS = """
SELECT
    ticker,
    quantidade_total,
    preco_medio,
    total_investido,
    posicao_atual,
    rentabilidade
FROM view_status_carteira
ORDER BY rentabilidade DESC
"""


QUERY_ATIVOS_COM_SALDO = """
SELECT DISTINCT ticker 
FROM view_status_carteira 
WHERE quantidade_total > 0
"""


QUERY_LOG_TRANSACOES = """
SELECT
    id_transacao,
    ticker,
    quantidade,
    preco_transacao,
    data_transacao,
    tipo_transacao
FROM view_transacoes
ORDER BY id_transacao DESC
"""


QUERY_RETORNO_TRANSACOES = """
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
        LAG(preco_medio_momento) OVER (PARTITION BY id_ativo ORDER BY id_transacao) as preco_medio_momento_anterior
    FROM view_calculo_preco_medio
) c
JOIN view_transacoes t ON t.id_transacao = c.id_transacao
ORDER BY t.id_transacao DESC;
"""


QUERY_EVOLUCAO_PATRIMONIO = "SELECT * FROM view_evolucao_patrimonio"
    

QUERY_RESULTADO_REALIZADO_TOTAL = """
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
        SELECT *, LAG(preco_medio_momento) OVER (PARTITION BY id_ativo ORDER BY id_transacao) as preco_medio_momento_anterior
        FROM view_calculo_preco_medio
    ) c
    JOIN view_transacoes t ON t.id_transacao = c.id_transacao
    WHERE t.tipo_transacao = 'Venda'
) sub
GROUP BY ticker
ORDER BY lucro_total_realizado DESC
"""