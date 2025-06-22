-- Criação da tabela de organizações/empresas
CREATE TABLE IF NOT EXISTS organizacoes (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    responsavel TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criação da tabela de respostas dos diagnósticos
CREATE TABLE IF NOT EXISTS respostas_diagnostico (
    id SERIAL PRIMARY KEY,
    organizacao_id INTEGER REFERENCES organizacoes(id) ON DELETE CASCADE,
    variavel VARCHAR(10) NOT NULL,
    pergunta_numero INTEGER NOT NULL,
    nota INTEGER CHECK (nota >= 0 AND nota <= 5),
    peso NUMERIC(4,2),
    respondido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para busca rápida
CREATE INDEX IF NOT EXISTS idx_org_nome_resp ON organizacoes (nome, responsavel);
CREATE INDEX IF NOT EXISTS idx_respostas_orgid ON respostas_diagnostico (organizacao_id);