import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import os
import openai

from ajuda_drexus import ajuda

st.set_page_config(page_title="Diagnóstico ICE³-R + DREXUS", layout="wide")

def conectar_banco():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        st.stop()

# --- BOTÃO PARA RESETAR BANCO DE DADOS ---

def reset_database():
    conn = conectar_banco()
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE IF EXISTS respostas_diagnostico CASCADE;")
        cur.execute("DROP TABLE IF EXISTS organizacoes CASCADE;")
        cur.execute("""
        CREATE TABLE organizacoes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            matricula TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE respostas_diagnostico (
            id SERIAL PRIMARY KEY,
            organizacao_id INTEGER REFERENCES organizacoes(id) ON DELETE CASCADE,
            variavel VARCHAR(10) NOT NULL,
            pergunta_numero INTEGER NOT NULL,
            nota INTEGER CHECK (nota >= 0 AND nota <= 5),
            peso NUMERIC(4,2),
            respondido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_org_nome_resp_matricula ON organizacoes (nome, responsavel, matricula);
        CREATE INDEX idx_respostas_orgid ON respostas_diagnostico (organizacao_id);
        """)
        conn.commit()
        st.success("Banco de dados resetado e recriado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao resetar banco de dados: {e}")
    finally:
        cur.close()
        conn.close()

st.sidebar.markdown("**Projeto DREXUS ICE³-R + DRE**")
if st.sidebar.button("Resetar Banco de Dados"):
    reset_database()

# Botão para diagnóstico agregado da empresa
if st.sidebar.button("Diagnóstico da Empresa"):
    st.session_state["modo_diagnostico_empresa"] = True
    st.rerun()


from dotenv import load_dotenv

if "resumo_gerado" not in st.session_state:
    st.session_state["resumo_gerado"] = False

# Variável para controlar o resumo da empresa
if "resumo_empresa_gerado" not in st.session_state:
    st.session_state["resumo_empresa_gerado"] = False

# ---------- CONFIGURAÇÕES INICIAIS ----------

if "empresa_input" not in st.session_state:
    st.session_state["empresa_input"] = ""
if "responsavel_input" not in st.session_state:
    st.session_state["responsavel_input"] = ""

load_dotenv()

# ---------- FUNÇÕES AUXILIARES ----------

def carregar_conhecimento_drexus():

    with open("dossie_drexus_ice3r_dre.md", encoding="utf-8") as f:
        return f.read()

def gerar_resumo_openai(empresa, responsavel, matricula, respostas, medias, rexp, zona, conhecimento_drexus):
    from openai import OpenAI
    client = OpenAI()
    prompt = f"""
    Empresa: {empresa}
    Responsável: {responsavel}
    Matrícula: {matricula}
    Respostas brutas: {respostas}
    Médias das variáveis: {medias}
    Rexp: {rexp}
    Zona de maturidade: {zona}
    Contexto do DREXUS: {conhecimento_drexus}

    Faça um resumo detalhado da situação da empresa, identifique vulnerabilidades e sugira as 5 principais ações prioritárias e objetivas para evolução imediata. Seja claro e prático.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um consultor especialista em organizações regenerativas e maturidade organizacional."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.7
    )
    return response.choices[0].message.content     

def autenticar():
    app_password = os.getenv("APP_PASSWORD")
    if app_password:
        senha = st.text_input("Senha de acesso", type="password")
        if senha != app_password:
            st.warning("Acesso restrito. Informe a senha correta.")
            st.stop()

def criar_tabelas():
    # Executa o schema.sql se desejar garantir a estrutura
    schema = """
    CREATE TABLE IF NOT EXISTS organizacoes (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        responsavel TEXT NOT NULL,
        matricula TEXT NOT NULL,
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
    CREATE INDEX IF NOT EXISTS idx_org_nome_resp_matricula ON organizacoes (nome, responsavel, matricula);
    CREATE INDEX IF NOT EXISTS idx_respostas_orgid ON respostas_diagnostico (organizacao_id);
    """
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute(schema)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao criar tabelas: {e}")

def salvar_diagnostico(empresa, responsavel, matricula, respostas):
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO organizacoes (nome, responsavel, matricula) VALUES (%s, %s, %s) RETURNING id",
            (empresa, responsavel, matricula)
        )
        org_id = cur.fetchone()[0]
        for var, valores in respostas.items():
            for idx, (nota, peso) in enumerate(valores, 1):
                cur.execute("""
                    INSERT INTO respostas_diagnostico (organizacao_id, variavel, pergunta_numero, nota, peso)
                    VALUES (%s, %s, %s, %s, %s)
                """, (org_id, var, idx, nota, peso))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Respostas salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")

def buscar_ultimo_diagnostico(empresa, responsavel, matricula):
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id FROM organizacoes o
            WHERE o.nome = %s AND o.responsavel = %s AND o.matricula = %s
            ORDER BY o.criado_em DESC LIMIT 1
        """, (empresa, responsavel, matricula))
        org = cur.fetchone()
        if not org:
            return None
        org_id = org[0]
        cur.execute("""
            SELECT variavel, pergunta_numero, nota, peso FROM respostas_diagnostico
            WHERE organizacao_id = %s
            ORDER BY variavel, pergunta_numero
        """, (org_id,))
        dados = cur.fetchall()
        cur.close()
        conn.close()
        respostas = {}
        for var, qnum, nota, peso in dados:
            if var not in respostas:
                respostas[var] = []
            respostas[var].append((nota, peso))
        return respostas
    except Exception as e:
        st.error(f"Erro ao buscar diagnóstico anterior: {e}")
        return None

def buscar_media_empresa(nome_empresa):
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        
        # Primeiro, busca todos os IDs da organização com este nome
        cur.execute("""
            SELECT id FROM organizacoes
            WHERE LOWER(nome) = LOWER(%s)
        """, (nome_empresa.lower(),))
        
        org_ids = [row[0] for row in cur.fetchall()]
        
        if not org_ids:
            st.error(f"Nenhum registro encontrado para a empresa '{nome_empresa}'")
            return None
            
        # Para cada variável e número de pergunta, calcula a média das notas
        medias_perguntas = {}
        
        for var in perguntas.keys():
            medias_perguntas[var] = []
            
            for i in range(1, len(perguntas[var]) + 1):
                cur.execute("""
                    SELECT AVG(nota) as media_nota, AVG(peso) as media_peso
                    FROM respostas_diagnostico
                    WHERE organizacao_id = ANY(%s)
                    AND variavel = %s
                    AND pergunta_numero = %s
                """, (org_ids, var, i))
                
                resultado = cur.fetchone()
                if resultado and resultado[0]:
                    media_nota = float(resultado[0])
                    media_peso = float(resultado[1])
                    medias_perguntas[var].append((media_nota, media_peso))
                else:
                    # Se não houver dados, usa o peso padrão e nota zero
                    peso_padrao = perguntas[var][i-1][1]
                    medias_perguntas[var].append((0.0, peso_padrao))
        
        cur.close()
        conn.close()
        
        st.success(f"Dados agregados de {len(org_ids)} diagnósticos da empresa '{nome_empresa}'")
        return medias_perguntas
        
    except Exception as e:
        st.error(f"Erro ao buscar dados da empresa: {e}")
        return None

# ---------- ESTRUTURA DAS PERGUNTAS ----------
# Para facilitar a leitura, as perguntas são resumidas (adicione todas para produção!)

perguntas = {
    "If": [
        ("A missão crítica da unidade está claramente definida e operacionalizada?", 0.15),
        ("Os processos essenciais operam sob contingência mínima com autonomia funcional?", 0.10),
        ("A cadeia de decisão se mantém funcional durante eventos extremos?", 0.15),
        ("As equipes conhecem e priorizam a missão crítica sob pressão?", 0.10),
        ("Há redundância mínima viável para manter a integridade operacional?", 0.10),
        ("Os sistemas de controle de qualidade funcionam mesmo em contextos adversos?", 0.10),
        ("A liderança consegue reorganizar recursos rapidamente sem comprometer a missão?", 0.10),
        ("Existe teste periódico da resiliência dos processos críticos?", 0.05),
        ("Há indicadores de missão crítica com resposta em tempo real?", 0.10),
        ("A integridade dos processos é percebida e valorizada pela cultura da organização?", 0.05),
    ],
    "Cm": [
        ("A organização é composta por módulos autônomos?", 0.10),
        ("Os módulos podem operar independentemente se necessário?", 0.10),
        ("Existe flexibilidade para reorganização estrutural?", 0.10),
        ("Os módulos compartilham recursos de maneira eficiente?", 0.10),
        ("Há protocolos claros de comunicação entre módulos?", 0.10),
        ("Os módulos conseguem absorver choques sem impactar o todo?", 0.10),
        ("A modularidade é revisada periodicamente?", 0.10),
        ("Existem métricas de performance por módulo?", 0.10),
        ("Os módulos têm autonomia de decisão em situações críticas?", 0.10),
        ("A modularidade é percebida como valor estratégico?", 0.10),
    ],
    "Et": [
        ("A organização aprende com eventos inesperados?", 0.10),
        ("Há processos para capturar aprendizados de crises?", 0.10),
        ("Mudanças são implementadas rapidamente após eventos críticos?", 0.10),
        ("A cultura valoriza adaptação contínua?", 0.10),
        ("As equipes são treinadas para evolução contínua?", 0.10),
        ("Existe monitoramento dos aprendizados implementados?", 0.10),
        ("A evolução é mensurada por indicadores específicos?", 0.10),
        ("Os aprendizados são compartilhados entre equipes?", 0.10),
        ("Feedbacks de evolução são sistemáticos?", 0.10),
        ("A evolução é percebida como diferencial competitivo?", 0.10),
    ],
    "DREq": [
        ("A organização tem histórico de decisões regenerativas?", 0.10),
        ("As DREs são documentadas sistematicamente?", 0.10),
        ("Há indicadores de densidade de DREs?", 0.10),
        ("As DREs são debatidas em fóruns internos?", 0.10),
        ("A cultura incentiva decisões regenerativas?", 0.10),
        ("Existem líderes referência em DREs?", 0.10),
        ("As DREs são reconhecidas e celebradas?", 0.10),
        ("A densidade de DREs aumenta ao longo do tempo?", 0.10),
        ("As DREs impactam processos-chave?", 0.10),
        ("A densidade de DREs é percebida como estratégica?", 0.10),
    ],
    "Lc": [
        ("A organização identifica corretamente seu contexto de atuação?", 0.10),
        ("As decisões consideram variáveis contextuais?", 0.10),
        ("Há análise contínua de contexto?", 0.10),
        ("Mudanças contextuais são rapidamente percebidas?", 0.10),
        ("A lógica de decisão é adaptada ao contexto?", 0.10),
        ("Existem ferramentas para análise de contexto?", 0.10),
        ("A contextualização é debatida em reuniões?", 0.10),
        ("A lógica contextual é revisada periodicamente?", 0.10),
        ("As equipes compreendem o contexto em que atuam?", 0.10),
        ("A lógica contextual é vista como diferencial?", 0.10),
    ],
    "Im": [
        ("As DREs geram impacto além da organização?", 0.10),
        ("O impacto é monitorado sistematicamente?", 0.10),
        ("Há indicadores de impacto sistêmico?", 0.10),
        ("As partes interessadas percebem o impacto das DREs?", 0.10),
        ("O impacto influencia decisões futuras?", 0.10),
        ("O impacto sistêmico é debatido em fóruns internos?", 0.10),
        ("Existem parcerias para ampliar o impacto?", 0.10),
        ("O impacto sistêmico é comunicado externamente?", 0.10),
        ("O impacto é revisado periodicamente?", 0.10),
        ("O impacto sistêmico é visto como valor?", 0.10),
    ],
    "Pv": [
        ("A organização tem um propósito claro e vivo?", 0.10),
        ("O propósito é comunicado a todos?", 0.10),
        ("O propósito é revisado periodicamente?", 0.10),
        ("As decisões refletem o propósito?", 0.10),
        ("O propósito é debatido em todos os níveis?", 0.10),
        ("O propósito orienta a estratégia?", 0.10),
        ("O propósito é percebido externamente?", 0.10),
        ("O propósito é celebrado em conquistas?", 0.10),
        ("O propósito é adaptado quando necessário?", 0.10),
        ("O propósito vivo é reconhecido como diferencial?", 0.10),
    ],
}


nomes_longos = {
    "If": "Integridade Funcional",
    "Cm": "Capacidade de Modularidade",
    "Et": "Evolução sob Estresse",
    "DREq": "Densidade de DREs",
    "Lc": "Lógica Contextual",
    "Im": "Impacto Sistêmico das DREs",
    "Pv": "Propósito Vivo",
}

# ---------- LÓGICA DE CÁLCULO ----------

def calcular_medias(respostas):
    medias = dict()
    for var, vals in respostas.items():
        notas = [nota for nota, peso in vals]
        pesos = [peso for nota, peso in vals]
        if sum(pesos) > 0:
            media = sum(n * p for n, p in zip(notas, pesos)) / sum(pesos)
        else:
            media = 0
        medias[var] = round(media / 5, 3)  # var é só a sigla
    return medias

def calcular_rexp(medias):
    try:
        rexpb = medias["If"] * medias["Cm"] * medias["Et"]
        rexpa = 1 + medias["DREq"] * (1 + medias["Lc"] * medias["Im"] * medias["Pv"])
        rexp = round(rexpb * rexpa, 3)
        return rexp
    except KeyError:
        return None

def calcular_dimensoes(medias):
    # Retorna dicionário para radar
    return {
        "Cognitiva": round(
            medias.get("Lc", 0) * 0.5 + medias.get("Et", 0) * 0.3 + medias.get("DREq", 0) * 0.2, 3),
        "Estratégica": round(
            medias.get("Pv", 0) * 0.4 + medias.get("Im", 0) * 0.3 + medias.get("DREq", 0) * 0.3, 3),
        "Operacional": round(
            medias.get("If", 0) * 0.4 + medias.get("Cm", 0) * 0.3 + medias.get("Et", 0) * 0.3, 3),
        "Cultural": round(
            medias.get("Et", 0) * 0.4 + medias.get("DREq", 0) * 0.3 + medias.get("Pv", 0) * 0.3, 3),
    }

def interpretar_rexp(rexp):
    if rexp is None:
        return "Não calculado"
    elif rexp >= 0.80:
        return "Antifragilidade Regenerativa"
    elif rexp >= 0.60:
        return "Resiliência Estratégica"
    elif rexp >= 0.40:
        return "Maturidade Tática"
    elif rexp >= 0.20:
        return "Resiliência Reativa"
    else:
        return "Fragilidade Total"

# ---------- INTERFACE PRINCIPAL ----------

autenticar()

# Modo Diagnóstico da Empresa
if "modo_diagnostico_empresa" not in st.session_state:
    st.session_state["modo_diagnostico_empresa"] = False

if st.session_state.get("modo_diagnostico_empresa", False):
    st.title("Diagnóstico Agregado da Empresa")
    st.markdown("Este diagnóstico calcula a média de todas as respostas dadas pelos funcionários da empresa selecionada.")
    
    empresa_nome = st.text_input("Digite o nome da empresa:", "")
    
    if st.button("Buscar e Calcular Médias"):
        if empresa_nome:
            with st.spinner("Buscando dados e calculando médias..."):
                respostas_medias = buscar_media_empresa(empresa_nome)
                
                if respostas_medias:
                    st.session_state["empresa_atual"] = empresa_nome
                    st.session_state["respostas_medias"] = respostas_medias
                    # Reset do estado do resumo quando buscamos novos dados
                    st.session_state["resumo_empresa_gerado"] = False
                    if "resumo_empresa" in st.session_state:
                        del st.session_state["resumo_empresa"]
                    
                    # Calcular métricas com base nas médias
                    medias = calcular_medias(respostas_medias)
                    rexp = calcular_rexp(medias)
                    zona = interpretar_rexp(rexp)
                    
                    # Salvar os dados calculados no estado da sessão
                    st.session_state["empresa_medias"] = medias
                    st.session_state["empresa_rexp"] = rexp
                    st.session_state["empresa_zona"] = zona
                    
                    # Exibir resultados
                    st.success(f"Rexp calculado: **{rexp}**")
                    st.metric("Zona de Maturidade", zona)
                    
                    # Gráfico radar
                    dimensoes = calcular_dimensoes(medias)
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=list(dimensoes.values()),
                        theta=list(dimensoes.keys()),
                        fill='toself',
                        name='Maturidade'
                    ))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabela de médias por variável
                    st.subheader("Médias por Dimensão")
                    df = pd.DataFrame([
                        {"Variável": nomes_longos[k], "Média Ponderada (0-1)": v}
                        for k, v in medias.items()
                    ])
                    st.dataframe(df, use_container_width=True)
                    
                    # Mostrar todos os sliders com as médias calculadas
                    st.subheader("Detalhamento por Pergunta (Valores Médios)")
                    
                    tab_names = list(perguntas.keys())
                    tabs = st.tabs(tab_names)
                    
                    for idx, var in enumerate(tab_names):
                        with tabs[idx]:
                            st.subheader(nomes_longos[var])
                            st.info(ajuda[var])
                            
                            for i, (pergunta, _) in enumerate(perguntas[var]):
                                media_nota, _ = respostas_medias[var][i]
                                st.slider(
                                    f"{i+1}. {pergunta}",
                                    min_value=0.0,
                                    max_value=5.0,
                                    value=float(media_nota),
                                    step=0.1,
                                    key=f"media_{var}_{i}",
                                    disabled=True  # Sliders bloqueados, apenas para visualização
                                )
                    
                    # MODIFICAÇÃO: Sistema de geração de resumo para a empresa com gerenciamento de estado
                    if not st.session_state.get("resumo_empresa_gerado", False):
                        if st.button("Gerar Resumo e Recomendações", key="gerar_resumo_empresa_btn"):
                            with st.spinner("Gerando análise e recomendações personalizadas..."):
                                conhecimento_drexus = carregar_conhecimento_drexus()
                                resumo = gerar_resumo_openai(
                                    empresa_nome,
                                    "Diagnóstico Agregado", 
                                    "N/A",
                                    respostas_medias,
                                    medias,
                                    rexp,
                                    zona,
                                    conhecimento_drexus
                                )
                                # Armazenar o resultado na sessão
                                st.session_state["resumo_empresa"] = resumo
                                st.session_state["resumo_empresa_gerado"] = True
                                # Recarregar para mostrar o resultado
                                st.rerun()
                    
                    # Mostrar o resumo se já foi gerado
                    if st.session_state.get("resumo_empresa_gerado", False):
                        st.subheader("Análise Agregada da Empresa:")
                        st.markdown(st.session_state["resumo_empresa"])
                        
                        # Botão para gerar um novo resumo
                        if st.button("Gerar Novo Resumo", key="gerar_novo_resumo_empresa_btn"):
                            st.session_state["resumo_empresa_gerado"] = False
                            if "resumo_empresa" in st.session_state:
                                del st.session_state["resumo_empresa"]
                            st.rerun()
        else:
            st.warning("Por favor, digite o nome da empresa.")
    
    if st.button("Voltar ao Diagnóstico Normal"):
        st.session_state["modo_diagnostico_empresa"] = False
        # Limpar estados relacionados ao diagnóstico da empresa
        if "empresa_atual" in st.session_state:
            del st.session_state["empresa_atual"]
        if "respostas_medias" in st.session_state:
            del st.session_state["respostas_medias"]
        if "resumo_empresa" in st.session_state:
            del st.session_state["resumo_empresa"]
        st.session_state["resumo_empresa_gerado"] = False
        st.rerun()
        
    # Parar o fluxo normal do app
    st.stop()

# Fluxo normal do app continua aqui
st.title("Diagnóstico ICE³-R + DREXUS")
st.markdown("Aplicação para diagnóstico de maturidade organizacional regenerativa usando o Teorema ICE³-R + DRE.")

empresa = st.text_input("Nome da Empresa", key="empresa_input").strip().lower()
responsavel = st.text_input("Nome do Responsável", key="responsavel_input").strip().lower()
matricula = st.text_input("Matrícula do Funcionário", key="matricula_input").strip().lower()

if not empresa or not responsavel or not matricula:
    st.info("Preencha o nome da empresa, do responsável e a matrícula para iniciar o diagnóstico.")
    st.stop()

# Novo bloco: Botão para iniciar o questionário
if "iniciar_questionario" not in st.session_state:
    st.session_state["iniciar_questionario"] = False

if not st.session_state["iniciar_questionario"]:
    if st.button("Iniciar Questionário"):
        st.session_state["iniciar_questionario"] = True
    else:
        st.stop()

criar_tabelas()

# Verifica se já existe diagnóstico:

ultimo = buscar_ultimo_diagnostico(empresa, responsavel, matricula)

if ultimo:
    st.info(f"Diagnóstico anterior encontrado para esta empresa/responsável/matrícula ({matricula}).")
    if st.checkbox("Deseja visualizar o diagnóstico anterior?"):
        medias_last = calcular_medias(ultimo)
        rexp_last = calcular_rexp(medias_last)
        st.success(f"Rexp anterior: **{rexp_last}**")
        st.metric("Zona de Maturidade", interpretar_rexp(rexp_last))
        st.write("Média das variáveis:", medias_last)
        dim_last = calcular_dimensoes(medias_last)
        fig_last = go.Figure()
        fig_last.add_trace(go.Scatterpolar(
            r=list(dim_last.values()),
            theta=list(dim_last.keys()),
            fill='toself',
            name='Maturidade'
        ))
        fig_last.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=False)
        st.plotly_chart(fig_last, use_container_width=True)


st.header("Novo Diagnóstico")

# Depois de preencher o dicionário respostas com os sliders:
# (mantém seu código anterior)

tab_names = list(perguntas.keys())  # ["If", "Cm", "Et", "DREq", "Lc", "Im", "Pv"]
tabs = st.tabs(tab_names)

respostas = {}

for idx, var in enumerate(tab_names):
    with tabs[idx]:
        st.subheader(nomes_longos[var])  # Nome longo APENAS dentro da aba
        st.info(ajuda[var])
        respostas[var] = []
        for i, (pergunta, peso) in enumerate(perguntas[var]):
            slider_key = f"{var}_{i}"
            valor_inicial = 0
            if ultimo and var in ultimo and len(ultimo[var]) > i:
                valor_inicial = ultimo[var][i][0]
            nota = st.slider(
                f"{i+1}. {pergunta}",
                0, 5,
                value=valor_inicial,
                key=slider_key
            )
            respostas[var].append((nota, peso))

# --- TRECHO QUE CONTROLA O BOTÃO ---

# Verifica se todas as perguntas foram respondidas (nenhum valor igual a zero)

if st.button("Calcular Rexp", key="calcular_rexp_btn"):
    medias = calcular_medias(respostas)
    rexp = calcular_rexp(medias)
    zona = interpretar_rexp(rexp)

    st.success(f"Rexp calculado: **{rexp}**")
    st.metric("Zona de Maturidade", zona)
    st.write("Média ponderada das variáveis:")
    
    for k, v in medias.items():
        st.write(f"{nomes_longos[k]}: {v}")

    dimensoes = calcular_dimensoes(medias)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(dimensoes.values()),
        theta=list(dimensoes.keys()),
        fill='toself',
        name='Maturidade'
    ))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tabela de Variáveis e Pesos")

    df = pd.DataFrame([
    {"Variável": nomes_longos[k], "Média Ponderada (0-1)": v}
    for k, v in medias.items()
    ])
    st.dataframe(df, use_container_width=True)

    st.session_state["resumo_gerado"] = False
    st.session_state["dados_resultado"] = {
        "empresa": empresa,
        "responsavel": responsavel,
        "matricula": matricula,
        "respostas": respostas,
        "medias": medias,
        "rexp": rexp,
        "zona": zona
    }

# Só mostra botão de resumo se já calculou e não gerou ainda

if st.session_state.get("dados_resultado") and not st.session_state["resumo_gerado"]:
    if st.button("Gerar Resumo e Recomendações Personalizadas"):
        dados = st.session_state["dados_resultado"]
        conhecimento_drexus = carregar_conhecimento_drexus()
        resumo = gerar_resumo_openai(
            dados["empresa"],
            dados["responsavel"],
            dados["matricula"],
            dados["respostas"],
            dados["medias"],
            dados["rexp"],
            dados["zona"],
            conhecimento_drexus
        )
        
        st.session_state["resumo"] = resumo
        st.session_state["resumo_gerado"] = True

if st.session_state.get("resumo_gerado", False):
    st.subheader("Resumo personalizado da situação da empresa:")
    st.markdown(st.session_state["resumo"])
    if st.button("Gravar diagnóstico no banco de dados"):
        dados = st.session_state["dados_resultado"]
        salvar_diagnostico(dados["empresa"], dados["responsavel"], dados["matricula"], dados["respostas"])        # Opcional: Limpar estado para novo diagnóstico
        st.session_state["resumo_gerado"] = False
        st.session_state["dados_resultado"] = None

        # Botão para resetar tudo e voltar ao início

if st.button("Novo Diagnóstico"):
    for var, lista_perguntas in perguntas.items():
        for i in range(len(lista_perguntas)):
            slider_key = f"{var}_{i}"
            if slider_key in st.session_state:
                del st.session_state[slider_key]
    st.session_state["iniciar_questionario"] = False
    st.session_state["resumo_gerado"] = False
    st.session_state["dados_resultado"] = None
    st.session_state["resumo"] = ""
    st.rerun()