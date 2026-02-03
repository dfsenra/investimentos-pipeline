-- =========================
-- Preço médio e posição
-- =========================

CREATE OR REPLACE VIEW vw_portfolio_positions AS
SELECT
    a.asset_id,
    a.ticker,
    SUM(t.quantidade) AS quantidade_total,
    SUM(t.quantidade * t.preco_compra) / SUM(t.quantidade) AS preco_medio,
    SUM(t.quantidade * t.preco_compra) AS total_investido
FROM portfolio_transactions t
JOIN assets a ON a.asset_id = t.asset_id
GROUP BY a.asset_id, a.ticker;


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
    (lp.close_price - p.preco_medio) / p.preco_medio AS rentabilidade
FROM vw_portfolio_positions p
JOIN vw_last_prices lp ON lp.asset_id = p.asset_id;


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
