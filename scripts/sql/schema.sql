CREATE TABLE IF NOT EXISTS ativos (
    id_ativo SERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    tipo_ativo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS precos (
    id_precos SERIAL PRIMARY KEY,
    id_ativo INTEGER REFERENCES ativos(id_ativo),
    data DATE NOT NULL,
    preco_abertura NUMERIC,
    preco_max NUMERIC,
    preco_min NUMERIC,
    preco_fechamento NUMERIC,
    volume BIGINT,
    fonte TEXT,
    CONSTRAINT data_unica_operacao_ativo UNIQUE (id_ativo, data)
);

CREATE TABLE IF NOT EXISTS transacoes_portfolio (
    id_transacao SERIAL PRIMARY KEY,
    id_ativo INTEGER NOT NULL REFERENCES ativos(id_ativo),
    data_transacao DATE NOT NULL,
    quantidade NUMERIC(18,6) NOT NULL,
    preco_transacao NUMERIC(18,6) NOT NULL,
    tipo_transacao TEXT NOT NULL

);

CREATE INDEX IF NOT EXISTS indice_transacao_ativo
    ON transacoes_portfolio(id_ativo);

CREATE INDEX IF NOT EXISTS indice_transacao_data
    ON transacoes_portfolio(data_transacao);

-- Essa função foi necessária para remover um bug. Após deletar registros/transações, ela garante que ativos sem transações sejam removidos para manter o menu suspenso limpo/correto
CREATE OR REPLACE FUNCTION limpar_lista_suspensa()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM ativos 
    WHERE id_ativo NOT IN (SELECT DISTINCT id_ativo FROM transacoes_portfolio)
    AND tipo_ativo = 'ativo';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_lista_suspensa
AFTER DELETE ON transacoes_portfolio
FOR EACH STATEMENT
EXECUTE FUNCTION limpar_lista_suspensa();
