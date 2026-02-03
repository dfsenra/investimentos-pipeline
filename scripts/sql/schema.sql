# Comecei salvando tudo em uma única tabela, mas tive problemas com indexação, tickers repetidos, erros de cálculos
# Lendo conteúdos sobre controle de finanças vi que o ideal é ter um "livro de registros" para anotar todas as compras/vendas
# Como o material estava em inglês acabei deixando os nomes em inglês


CREATE TABLE IF NOT EXISTS assets (
    asset_id SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    price_id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(asset_id),
    data DATE NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume BIGINT,
    source TEXT,
    UNIQUE (asset_id, data)
);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
    transaction_id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    data_compra DATE NOT NULL,
    quantidade NUMERIC(18,6) NOT NULL,
    preco_compra NUMERIC(18,6) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_asset
    ON portfolio_transactions(asset_id);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_date
    ON portfolio_transactions(data_compra);

CREATE TABLE IF NOT EXISTS portfolio_daily (
    date DATE PRIMARY KEY,
    portfolio_price NUMERIC(14,4) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
