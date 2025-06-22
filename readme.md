# DREXUS ICE³-R + DRE Diagnóstico

Aplicação web (Streamlit + Python) para diagnóstico de maturidade organizacional regenerativa, baseada no Teorema ICE³-R + DRE (Decisões Regenerativas Exponenciais). Permite coleta, cálculo, dashboard e armazenamento seguro dos dados em PostgreSQL na nuvem.

---

## 🚀 Funcionalidades

- Formulário interativo com 70 perguntas (7 variáveis, 10 por aba, sliders 0–5)
- Cálculo automático do índice Rexp e zona de maturidade
- Radar visual das 4 dimensões (Cognitiva, Estratégica, Operacional, Cultural)
- Histórico por organização/empresa
- Gravação segura dos dados no banco PostgreSQL (Render.com)
- Pronto para integração com IA/RAG
- Deploy rápido via Render e integração GitHub

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
     ```

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

4. Render detecta o `Procfile` e executa:
   ```
   web: streamlit run app.py --server.port=$PORT
   ```

5. Pronto! O app estará no ar, 100% em nuvem.

---

## 🧠 Uso

- Acesse o app.
- Informe o nome da empresa e responsável.
- Responda às perguntas, navegue entre as abas.
- Clique para calcular resultados.
- Veja o radar e zona de maturidade.
- Salve no banco se desejar.

---

## 🔒 Segurança

- Nunca exponha seu `.env` real no repositório.
- Use variáveis de ambiente no Render ou serviços similares.
- O acesso pode ser protegido por senha (`APP_PASSWORD`).

---

## 📄 Licença

MIT License.

---

## 👨‍💻 Contato

Dúvidas, sugestões ou contribuições? Abra uma issue ou envie um PR!

