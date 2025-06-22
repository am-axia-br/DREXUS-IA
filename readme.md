# DREXUS ICE³-R + DRE Diagnóstico

Aplicação web (Streamlit + Python) para diagnóstico de maturidade organizacional regenerativa, baseada no Teorema ICE³-R + DRE (Decisões Regenerativas Exponenciais). Permite coleta, cálculo, dashboard, análise inteligente com IA e armazenamento seguro dos dados em PostgreSQL na nuvem.

---

## 🚀 Funcionalidades

- Formulário interativo com 70 perguntas (7 variáveis, 10 por aba, sliders 0–5)
- Cálculo automático do índice Rexp e zona de maturidade
- Radar visual das 4 dimensões (Cognitiva, Estratégica, Operacional, Cultural)
- Histórico por organização/empresa
- **Resumo inteligente e recomendações de ações** (OpenAI GPT-4o, contexto Drexus)
- Gravação segura dos dados no banco PostgreSQL (Render.com) _apenas após análise IA_
- Deploy rápido via Render e integração GitHub

---

## 🧠 Como funciona o fluxo de uso

1. O usuário informa a empresa e o responsável.
2. Responde ao questionário (navegando entre as abas).
3. Clica em **Calcular Rexp** — vê resultados, radar e zona de maturidade.
4. Tem a opção de clicar em **Gerar Resumo e Recomendações Personalizadas**.
5. O app gera, via IA (OpenAI + contexto Drexus), um diagnóstico detalhado e as 5 principais ações recomendadas.
6. Só após ler o resumo, o usuário pode clicar em **Gravar diagnóstico no banco de dados**.
7. O ciclo pode ser repetido, sempre com o diagnóstico inteligente antes de gravar.

---

## 📁 Estrutura do Projeto

```
DREXUS/
├── app.py
├── requirements.txt
├── Procfile
├── schema.sql
├── .env.example
├── README.md
├── DOSSIE_DREXUS_ICE3R_DRE.md
├── src/
│   ├── __init__.py
│   ├── db.py
│   ├── perguntas.py
│   └── calculos.py
├── assets/
├── notebooks/
└── data/
```

---

## 🛠️ Instalação Local

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/DREXUS.git
   cd DREXUS
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure as variáveis de ambiente:
   - Copie o `.env.example` para `.env` e preencha:
     ```
     DATABASE_URL=postgres://usuario:senha@host:5432/nome_banco
     APP_PASSWORD=sua_senha_segura
     OPENAI_API_KEY=sua_chave_openai_aqui
     ```
   - **Atenção:** a variável `OPENAI_API_KEY` é obrigatória para a etapa de resumo inteligente.

4. (Opcional) Crie o banco de dados usando o `schema.sql` no PostgreSQL.

5. Execute a aplicação:
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Deploy na Nuvem (Render)

1. Suba este repositório no GitHub.

2. No Render.com, crie um novo **Web Service** a partir do repositório.

3. Configure as variáveis de ambiente:
   - `DATABASE_URL` (string de conexão PostgreSQL da Render)
   - `APP_PASSWORD` (senha de acesso, se desejar)
   - `OPENAI_API_KEY` (sua chave da OpenAI)

4. Render detecta o `Procfile` e executa:
   ```
   web: streamlit run app.py --server.port=$PORT
   ```

5. Pronto! O app estará no ar, 100% em nuvem, com IA ativa.

---

## 🧠 Inteligência Artificial integrada

- O diagnóstico apresenta um **resumo personalizado** e recomendações automáticas, baseadas nas respostas, resultados e no conhecimento do DREXUS (arquivo `DOSSIE_DREXUS_ICE3R_DRE.md`).
- A geração do resumo utiliza a API do OpenAI, com modelo GPT-4o.
- O usuário só pode gravar no banco após ler o diagnóstico da IA.

---

## 🛡️ Segurança

- Nunca exponha seu `.env` real no repositório.
- Use variáveis de ambiente no Render ou serviços similares.
- O acesso pode ser protegido por senha (`APP_PASSWORD`).
- Sua chave da OpenAI (`OPENAI_API_KEY`) deve ser mantida secreta.

---

## 📄 Licença

MIT License.

---

## 👨‍💻 Contato

Dúvidas, sugestões ou contribuições?  
Abra uma issue ou envie um PR!