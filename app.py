import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import os
import openai

from dotenv import load_dotenv

if "resumo_gerado" not in st.session_state:
    st.session_state["resumo_gerado"] = False

# ---------- CONFIGURAÇÕES INICIAIS ----------

st.set_page_config(page_title="Diagnóstico ICE³-R + DREXUS", layout="wide")
load_dotenv()

# ---------- FUNÇÕES AUXILIARES ----------

def carregar_conhecimento_drexus():

    with open("dossie_drexus_ice3r_dre.md", encoding="utf-8") as f:
        return f.read()

def gerar_resumo_openai(empresa, responsavel, respostas, medias, rexp, zona, conhecimento_drexus):
    from openai import OpenAI
    client = OpenAI()
    prompt = f"""
    Empresa: {empresa}
    Responsável: {responsavel}
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

def conectar_banco():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        st.stop()

def criar_tabelas():
    # Executa o schema.sql se desejar garantir a estrutura
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

def salvar_diagnostico(empresa, responsavel, respostas):
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO organizacoes (nome, responsavel) VALUES (%s, %s) RETURNING id",
            (empresa, responsavel)
        )
        org_id = cur.fetchone()[0]
        for var, valores in respostas.items():
            var_sigla = var.split(" –")[0]
            for idx, (nota, peso) in enumerate(valores, 1):
                cur.execute("""
                    INSERT INTO respostas_diagnostico (organizacao_id, variavel, pergunta_numero, nota, peso)
                    VALUES (%s, %s, %s, %s, %s)
                """, (org_id, var_sigla, idx, nota, peso))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Respostas salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")

def buscar_ultimo_diagnostico(empresa, responsavel):
    try:
        conn = conectar_banco()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id FROM organizacoes o
            WHERE o.nome = %s AND o.responsavel = %s
            ORDER BY o.criado_em DESC LIMIT 1
        """, (empresa, responsavel))
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
        # Reconstrói respostas agrupadas para exibição
        respostas = {}
        for var, qnum, nota, peso in dados:
            if var not in respostas:
                respostas[var] = []
            respostas[var].append((nota, peso))
        return respostas
    except Exception as e:
        st.error(f"Erro ao buscar diagnóstico anterior: {e}")
        return None

# ---------- ESTRUTURA DAS PERGUNTAS ----------
# Para facilitar a leitura, as perguntas são resumidas (adicione todas para produção!)
perguntas = {
    "If – Integridade Funcional": [
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
    "Cm – Capacidade de Modularidade": [
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
    "Et – Evolução sob Estresse": [
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
    "DREq – Densidade de DREs": [
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
    "Lc – Lógica Contextual": [
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
    "Im – Impacto Sistêmico das DREs": [
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
    "Pv – Propósito Vivo": [
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
    ]
}

variaveis_siglas = {
    "If – Integridade Funcional": "If",
    "Cm – Capacidade de Modularidade": "Cm",
    "Et – Evolução sob Estresse": "Et",
    "DREq – Densidade de DREs": "DREq",
    "Lc – Lógica Contextual": "Lc",
    "Im – Impacto Sistêmico das DREs": "Im",
    "Pv – Propósito Vivo": "Pv",
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
        medias[variaveis_siglas[var]] = round(media / 5, 3)  # Normaliza em 0-1
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
st.title("Diagnóstico ICE³-R + DREXUS")
st.markdown("Aplicação para diagnóstico de maturidade organizacional regenerativa usando o Teorema ICE³-R + DRE.")

st.sidebar.markdown("**Projeto DREXUS ICE³-R + DRE**")
#st.sidebar.markdown("Powered by Streamlit + PostgreSQL + Plotly")
#st.sidebar.markdown("[Manual e documentação](https://github.com/seu-usuario/DREXUS)")


empresa = st.text_input("Nome da Empresa", key="empresa_input").strip().lower()
responsavel = st.text_input("Nome do Responsável", key="responsavel_input").strip().lower()

if not empresa or not responsavel:
    st.info("Preencha o nome da empresa e do responsável para iniciar o diagnóstico.")
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

ultimo = buscar_ultimo_diagnostico(empresa, responsavel)
if ultimo:
    st.info("Diagnóstico anterior encontrado para esta empresa/responsável.")
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
else:
    st.warning("Nenhum diagnóstico encontrado para esta empresa/responsável.")


st.header("Novo Diagnóstico")

# Depois de preencher o dicionário respostas com os sliders:
# (mantém seu código anterior)

tabs = st.tabs(list(perguntas.keys()))
respostas = {}
for idx, (var, lista_perguntas) in enumerate(perguntas.items()):
    with tabs[idx]:
        st.subheader(f"{var}")
        respostas[var] = []
        for i, (pergunta, peso) in enumerate(lista_perguntas):
            slider_key = f"{var}_{i}"
            valor_inicial = 0
            # Se já existe diagnóstico anterior, preenche o valor inicial
            if ultimo and var in ultimo and len(ultimo[var]) > i:
                valor_inicial = ultimo[var][i][0]
            # Garante que o valor inicial só é setado se ainda não existe na session_state
            if slider_key not in st.session_state:
                st.session_state[slider_key] = valor_inicial
            nota = st.slider(
                f"{i+1}. {pergunta}",
                0, 5,
                st.session_state[slider_key],
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
    st.write("Média ponderada das variáveis:", medias)

    dimensoes = calcular_dimensoes(medias)
    st.subheader("Radar das Dimensões")
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
        {"Variável": k, "Média Ponderada (0-1)": v}
        for k, v in medias.items()
    ])
    st.dataframe(df, use_container_width=True)

    st.session_state["resumo_gerado"] = False
    st.session_state["dados_resultado"] = {
        "empresa": empresa,
        "responsavel": responsavel,
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
        salvar_diagnostico(dados["empresa"], dados["responsavel"], dados["respostas"])
        # Opcional: Limpar estado para novo diagnóstico
        st.session_state["resumo_gerado"] = False
        st.session_state["dados_resultado"] = None

        # Botão para resetar tudo e voltar ao início

    if st.button("Novo Diagnóstico"):
        st.session_state["iniciar_questionario"] = False
        st.session_state["resumo_gerado"] = False
        st.session_state["dados_resultado"] = None
        st.session_state["resumo"] = ""
        st.session_state["empresa_input"] = ""
        st.session_state["responsavel_input"] = ""
        # Limpa sliders:
        for var, lista_perguntas in perguntas.items():
            for i in range(len(lista_perguntas)):
                slider_key = f"{var}_{i}"
                if slider_key in st.session_state:
                    del st.session_state[slider_key]
        st.experimental_rerun()