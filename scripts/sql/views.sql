-- 1. Limpeza completa
DROP VIEW IF EXISTS vw_carteira_resumo CASCADE;
DROP VIEW IF EXISTS vw_portfolio_status CASCADE;
DROP VIEW IF EXISTS vw_asset_returns CASCADE;
DROP VIEW IF EXISTS vw_last_prices CASCADE;
DROP VIEW IF EXISTS vw_portfolio_transactions CASCADE;
DROP VIEW IF EXISTS vw_portfolio_positions CASCADE;
DROP VIEW IF EXISTS vw_calculo_medio_recursivo CASCADE;

-- 2. View de Cálculo com CASTS para evitar DatatypeMismatch
CREATE OR REPLACE VIEW vw_calculo_medio_recursivo AS
WITH RECURSIVE calculo AS (
    -- PARTE ÂNCORA
    SELECT 
        t.transaction_id, 
        t.asset_id, 
        CAST(t.quantidade AS NUMERIC) as qtd_acumulada,
        CAST((t.quantidade * t.preco_transacao) AS NUMERIC) as custo_total_acumulado,
        CAST(t.preco_transacao AS NUMERIC) as preco_medio_momento
    FROM portfolio_transactions t
    WHERE t.transaction_id = (SELECT min(transaction_id) FROM portfolio_transactions WHERE asset_id = t.asset_id)
    
    UNION ALL
    
    -- PARTE RECURSIVA
    SELECT 
        t.transaction_id, 
        t.asset_id,
        CAST(CASE WHEN t.tipo_transacao = 'Compra' THEN c.qtd_acumulada + t.quantidade ELSE c.qtd_acumulada - t.quantidade END AS NUMERIC),
        CAST(CASE 
            WHEN t.tipo_transacao = 'Compra' THEN c.custo_total_acumulado + (t.quantidade * t.preco_transacao)
            WHEN (c.qtd_acumulada - t.quantidade) <= 0 THEN 0
            ELSE c.custo_total_acumulado - (t.quantidade * c.preco_medio_momento)
        END AS NUMERIC),
        CAST(CASE 
            WHEN t.tipo_transacao = 'Compra' THEN (c.custo_total_acumulado + (t.quantidade * t.preco_transacao)) / (c.qtd_acumulada + t.quantidade)
            WHEN (c.qtd_acumulada - t.quantidade) <= 0 THEN 0
            ELSE c.preco_medio_momento
        END AS NUMERIC)
    FROM portfolio_transactions t
    INNER JOIN calculo c ON t.asset_id = c.asset_id 
    WHERE t.transaction_id = (SELECT min(transaction_id) FROM portfolio_transactions WHERE asset_id = t.asset_id AND transaction_id > c.transaction_id)
)
SELECT * FROM calculo;

-- 3. Recriar a vw_portfolio_positions (que o dashboard usa)
CREATE OR REPLACE VIEW vw_portfolio_positions AS
SELECT DISTINCT ON (asset_id)
    asset_id,
    (SELECT ticker FROM assets WHERE asset_id = c.asset_id) as ticker,
    qtd_acumulada AS quantidade_total,
    preco_medio_momento AS preco_medio,
    custo_total_acumulado AS total_investido
FROM vw_calculo_medio_recursivo c
ORDER BY asset_id, transaction_id DESC;


-- =========================
-- Preço médio e posição
-- =========================

CREATE OR REPLACE VIEW vw_portfolio_positions AS
SELECT DISTINCT ON (asset_id)
    asset_id,
    (SELECT ticker FROM assets WHERE asset_id = c.asset_id) as ticker,
    qtd_acumulada AS quantidade_total,
    preco_medio_momento AS preco_medio,
    custo_total_acumulado AS total_investido
FROM vw_calculo_medio_recursivo c
ORDER BY asset_id, transaction_id DESC; -- Pega sempre a última transação de cada ativo

-- ==================
-- Log de transações
-- ==================

CREATE OR REPLACE VIEW vw_portfolio_transactions AS
SELECT
    a.asset_id,
    a.ticker,
    t.transaction_id,
    t.data_transacao,
    t.quantidade,
    t.preco_transacao,
    t.tipo_transacao
FROM portfolio_transactions t
JOIN assets a ON a.asset_id = t.asset_id
ORDER BY t.data_transacao;


-- =========================
-- Último preço por ativo
-- =========================

CREATE OR REPLACE VIEW vw_last_prices AS
SELECT DISTINCT ON (asset_id)
    asset_id,
    data,
    close_price
FROM prices
ORDER BY asset_id, data DESC;


-- =========================
-- Status atual da carteira
-- =========================

CREATE OR REPLACE VIEW vw_portfolio_status AS
SELECT
    p.asset_id,
    p.ticker,
    p.quantidade_total,
    p.preco_medio,
    lp.close_price AS ultimo_preco,
    p.total_investido,
    p.quantidade_total * lp.close_price AS posicao_atual,
    -- Proteção contra divisão por zero usando NULLIF
    (lp.close_price - p.preco_medio) / NULLIF(p.preco_medio, 0) AS rentabilidade
FROM vw_portfolio_positions p
JOIN vw_last_prices lp ON lp.asset_id = p.asset_id
WHERE p.quantidade_total > 0; -- Esconde ativos zerados do Dashboard


-- =========================
-- Carteira agregada
-- =========================

CREATE OR REPLACE VIEW vw_carteira_resumo AS
SELECT
    SUM(total_investido) AS total_investido,
    SUM(posicao_atual) AS valor_atual,
    (SUM(posicao_atual) - SUM(total_investido)) / SUM(total_investido) AS rentabilidade
FROM vw_portfolio_status;


-- =========================
-- Retorno diário por ativo
-- =========================

CREATE OR REPLACE VIEW vw_asset_returns AS
SELECT
    a.ticker,
    p.data,
    p.close_price,
    CASE
        WHEN LAG(p.close_price) OVER (PARTITION BY a.asset_id ORDER BY p.data) IS NULL
        THEN NULL
        ELSE (p.close_price /
              LAG(p.close_price) OVER (PARTITION BY a.asset_id ORDER BY p.data) - 1)
    END AS retorno_diario
FROM prices p
JOIN assets a ON a.asset_id = p.asset_id;

-- ===============================================
-- Tipos de ativos: carteira ou índice de mercado
-- ===============================================

CREATE OR REPLACE VIEW ativos AS
SELECT ticker
FROM assets
WHERE asset_type = 'ativo';


CREATE OR REPLACE VIEW indices AS
SELECT ticker
FROM assets
WHERE asset_type = 'indice';


-- =====================
-- Evolução patrimonial
-- =====================

CREATE OR REPLACE VIEW vw_evolucao_patrimonio AS
WITH datas_assets AS (
    -- Gera a grade de todas as datas para todos os ativos
    SELECT DISTINCT p.data, a.asset_id, a.ticker
    FROM prices p
    CROSS JOIN assets a
    WHERE a.asset_type = 'ativo'
),
saldos_diarios AS (
    -- Para cada dia, busca a última transação ocorrida até aquela data
    SELECT 
        da.data,
        da.ticker,
        -- Busca o preço de fechamento do dia
        pr.close_price,
        -- Busca a quantidade acumulada até aquele momento
        COALESCE((
            SELECT c.qtd_acumulada 
            FROM vw_calculo_medio_recursivo c 
            JOIN portfolio_transactions t ON t.transaction_id = c.transaction_id
            WHERE t.asset_id = da.asset_id 
              AND t.data_transacao <= da.data
            ORDER BY t.data_transacao DESC, t.transaction_id DESC
            LIMIT 1
        ), 0) as qtd_no_dia
    FROM datas_assets da
    LEFT JOIN prices pr ON pr.asset_id = da.asset_id AND pr.data = da.data
)
SELECT 
    data,
    SUM(qtd_no_dia * close_price) as patrimonio_total
FROM saldos_diarios
GROUP BY data
HAVING SUM(qtd_no_dia * close_price) > 0
ORDER BY data;

