import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    Cria e retorna uma conexão com o banco de dados PostgreSQL usando a variável de ambiente DATABASE_URL.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise Exception("A variável de ambiente DATABASE_URL não está definida.")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

def criar_tabelas():
    """
    Cria as tabelas necessárias no banco de dados se não existirem.
    """
    schema = """
    CREATE TABLE IF NOT EXISTS organizacoes (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        responsavel TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS respostas_diagnostico (
        id SERIAL PRIMARY KEY,
        organizacao_id INTEGER REFERENCES organizacoes(id) ON DELETE CASCADE,
        variavel VARCHAR(10) NOT NULL,
        pergunta_numero INTEGER NOT NULL,
        nota INTEGER CHECK (nota >= 0 AND nota <= 5),
        peso NUMERIC(4,2),
        respondido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_org_nome_resp ON organizacoes (nome, responsavel);
    CREATE INDEX IF NOT EXISTS idx_respostas_orgid ON respostas_diagnostico (organizacao_id);
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(schema)
    conn.commit()
    cur.close()
    conn.close()

def salvar_diagnostico(empresa, responsavel, respostas):
    """
    Salva as respostas do diagnóstico no banco de dados.
    :param empresa: Nome da empresa
    :param responsavel: Nome do responsável
    :param respostas: Dicionário { variavel: [(nota, peso), ...], ... }
    """
    conn = get_connection()
    cur = conn.cursor()
    # Insere a organização e obtém o id
    cur.execute(
        "INSERT INTO organizacoes (nome, responsavel) VALUES (%s, %s) RETURNING id",
        (empresa, responsavel)
    )
    org_id = cur.fetchone()["id"]
    # Insere todas as respostas
    for var, valores in respostas.items():
        var_sigla = var.split(" –")[0] if " –" in var else var
        for idx, (nota, peso) in enumerate(valores, 1):
            cur.execute(
                """
                INSERT INTO respostas_diagnostico (organizacao_id, variavel, pergunta_numero, nota, peso)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (org_id, var_sigla, idx, nota, peso)
            )
    conn.commit()
    cur.close()
    conn.close()

def buscar_ultimo_diagnostico(empresa, responsavel):
    """
    Busca o último diagnóstico salvo para a empresa/responsável.
    :return: Respostas estruturadas { variavel: [(nota, peso), ...], ... } ou None
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id FROM organizacoes o
        WHERE o.nome = %s AND o.responsavel = %s
        ORDER BY o.criado_em DESC LIMIT 1
    """, (empresa, responsavel))
    org = cur.fetchone()
    if not org:
        cur.close()
        conn.close()
        return None
    org_id = org["id"]
    cur.execute("""
        SELECT variavel, pergunta_numero, nota, peso FROM respostas_diagnostico
        WHERE organizacao_id = %s
        ORDER BY variavel, pergunta_numero
    """, (org_id,))
    dados = cur.fetchall()
    cur.close()
    conn.close()
    # Reconstrói respostas agrupadas para exibição
    respostas = {}
    for row in dados:
        var = row["variavel"]
        if var not in respostas:
            respostas[var] = []
        respostas[var].append((row["nota"], float(row["peso"])))
    return respostas