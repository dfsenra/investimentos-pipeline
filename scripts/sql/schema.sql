CREATE TABLE IF NOT EXISTS assets (
    asset_id SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    asset_type TEXT NOT NULL
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
    CONSTRAINT unique_asset_date UNIQUE (asset_id, data)
);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
    transaction_id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    data_transacao DATE NOT NULL,
    quantidade NUMERIC(18,6) NOT NULL,
    preco_transacao NUMERIC(18,6) NOT NULL,
    tipo_transacao TEXT NOT NULL

);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_asset
    ON portfolio_transactions(asset_id);

CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_date
    ON portfolio_transactions(data_transacao);

CREATE TABLE IF NOT EXISTS portfolio_daily (
    date DATE PRIMARY KEY,
    portfolio_price NUMERIC(14,4) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Garante que ativos sem transações sejam removidos para manter a interface limpa
CREATE OR REPLACE FUNCTION fn_limpar_ativos_gastos()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM assets 
    WHERE asset_id NOT IN (SELECT DISTINCT asset_id FROM portfolio_transactions)
    AND asset_type = 'ativo';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_pos_delete_transacao
AFTER DELETE ON portfolio_transactions
FOR EACH STATEMENT
EXECUTE FUNCTION fn_limpar_ativos_gastos();
