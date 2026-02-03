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
# Carteira (resumo)
# =========================

CARTEIRA_RESUMO_QUERY = """
SELECT *
FROM vw_carteira_resumo
"""