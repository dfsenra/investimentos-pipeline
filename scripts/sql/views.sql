DROP VIEW IF EXISTS view_resumo_carteira CASCADE;
DROP VIEW IF EXISTS view_status_carteira CASCADE;
DROP VIEW IF EXISTS view_ganhos_carteira CASCADE;
DROP VIEW IF EXISTS view_ultimo_fechamento CASCADE;
DROP VIEW IF EXISTS view_transacoes CASCADE;
DROP VIEW IF EXISTS view_posicao_carteira CASCADE;
DROP VIEW IF EXISTS view_calculo_preco_medio CASCADE; 
DROP VIEW IF EXISTS view_evolucao_patrimonio CASCADE;
DROP VIEW IF EXISTS view_somente_ativos CASCADE; 
DROP VIEW IF EXISTS view_somente_indices CASCADE;

CREATE OR REPLACE VIEW view_calculo_preco_medio AS
WITH RECURSIVE calculo AS (

    SELECT 
        t.id_transacao, 
        t.id_ativo, 
        CAST(t.quantidade AS NUMERIC) as qtd_acumulada,
        CAST((t.quantidade * t.preco_transacao) AS NUMERIC) as custo_total_acumulado,
        CAST(t.preco_transacao AS NUMERIC) as preco_medio_momento
    FROM transacoes_portfolio t
    WHERE t.id_transacao = (SELECT min(id_transacao) FROM transacoes_portfolio WHERE id_ativo = t.id_ativo)
    
    UNION ALL
    
    SELECT 
        t.id_transacao, 
        t.id_ativo,
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
    FROM transacoes_portfolio t
    INNER JOIN calculo c ON t.id_ativo = c.id_ativo 
    WHERE t.id_transacao = (SELECT min(id_transacao) FROM transacoes_portfolio WHERE id_ativo = t.id_ativo AND id_transacao > c.id_transacao)
)
SELECT * FROM calculo;


CREATE OR REPLACE VIEW view_posicao_carteira AS
SELECT DISTINCT ON (id_ativo)
    id_ativo,
    (SELECT ticker FROM ativos WHERE id_ativo = c.id_ativo) as ticker,
    qtd_acumulada AS quantidade_total,
    preco_medio_momento AS preco_medio,
    custo_total_acumulado AS total_investido
FROM view_calculo_preco_medio c
ORDER BY id_ativo, id_transacao DESC;


CREATE OR REPLACE VIEW view_transacoes AS
SELECT
    a.id_ativo,
    a.ticker,
    t.id_transacao,
    t.data_transacao,
    t.quantidade,
    t.preco_transacao,
    t.tipo_transacao
FROM transacoes_portfolio t
JOIN ativos a ON a.id_ativo = t.id_ativo
ORDER BY t.data_transacao;


CREATE OR REPLACE VIEW view_ultimo_fechamento AS
SELECT DISTINCT ON (id_ativo)
    id_ativo,
    data,
    preco_fechamento
FROM precos
ORDER BY id_ativo, data DESC;


CREATE OR REPLACE VIEW view_status_carteira AS
SELECT
    p.id_ativo,
    p.ticker,
    p.quantidade_total,
    p.preco_medio,
    lp.preco_fechamento AS ultimo_preco,
    p.total_investido,
    p.quantidade_total * lp.preco_fechamento AS posicao_atual,
    (lp.preco_fechamento - p.preco_medio) / NULLIF(p.preco_medio, 0) AS rentabilidade
FROM view_posicao_carteira p
JOIN view_ultimo_fechamento lp ON lp.id_ativo = p.id_ativo
WHERE p.quantidade_total > 0;


CREATE OR REPLACE VIEW view_resumo_carteira AS
SELECT
    SUM(total_investido) AS total_investido,
    SUM(posicao_atual) AS valor_atual,
    (SUM(posicao_atual) - SUM(total_investido)) / SUM(total_investido) AS rentabilidade
FROM view_status_carteira;


CREATE OR REPLACE VIEW view_ganhos_carteira AS
SELECT
    a.ticker,
    p.data,
    p.preco_fechamento,
    CASE
        WHEN LAG(p.preco_fechamento) OVER (PARTITION BY a.id_ativo ORDER BY p.data) IS NULL
        THEN NULL
        ELSE (p.preco_fechamento /
              LAG(p.preco_fechamento) OVER (PARTITION BY a.id_ativo ORDER BY p.data) - 1)
    END AS retorno_diario
FROM precos p
JOIN ativos a ON a.id_ativo = p.id_ativo;


CREATE OR REPLACE VIEW somente_ativos AS
SELECT ticker
FROM ativos
WHERE tipo_ativo = 'ativo';


CREATE OR REPLACE VIEW somente_indices AS
SELECT ticker
FROM ativos
WHERE tipo_ativo = 'indice';


CREATE OR REPLACE VIEW view_evolucao_patrimonio AS
WITH datas_ativos AS (

    SELECT DISTINCT p.data, a.id_ativo, a.ticker
    FROM precos p
    CROSS JOIN ativos a
    WHERE a.tipo_ativo = 'ativo'
),
saldos_diarios AS (

    SELECT 
        da.data,
        da.ticker,
        pr.preco_fechamento,
        COALESCE((
            SELECT c.qtd_acumulada 
            FROM view_calculo_preco_medio c 
            JOIN transacoes_portfolio t ON t.id_transacao = c.id_transacao
            WHERE t.id_ativo = da.id_ativo 
              AND t.data_transacao <= da.data
            ORDER BY t.data_transacao DESC, t.id_transacao DESC
            LIMIT 1
        ), 0) as qtd_no_dia
    FROM datas_ativos da
    LEFT JOIN precos pr ON pr.id_ativo = da.id_ativo AND pr.data = da.data
)
SELECT 
    data,
    SUM(qtd_no_dia * preco_fechamento) as patrimonio_total
FROM saldos_diarios
GROUP BY data
HAVING SUM(qtd_no_dia * preco_fechamento) > 0
ORDER BY data;

