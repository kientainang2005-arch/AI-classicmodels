# ClassicModels AI: Natural-Language BI Assistant

Ask business questions in **Vietnamese or English** and get a SQL-backed answer: generated SQL, result table, chart and a short plain-language explanation. No SQL knowledge needed.

A personal learning project: a business user asks, and an LLM grounded in the company's own schema and KPI definitions (RAG) answers from live data, with guardrails.

## 1. Who is it for, and what problem does it solve?

| User | Pain today | What they get |
|---|---|---|
| Head of Sales / sales manager | Waits for the data team for every ad-hoc number | Self-service answers in seconds ("Top 5 best-selling products?") |
| CEO / management | Dashboards answer fixed questions only | Strategic answers on revenue and best sales reps, framed for decisions |
| Data / BI analyst | Drowning in repetitive report requests | Sees the generated SQL, can verify or reuse it; fewer tickets |
| New joiner / trainee | Does not know the schema | "Technical Mentor" role explains which tables to JOIN and why |

**Business value:** shorter time-to-insight, fewer one-off report requests, and a consistent definition of every KPI (revenue, margin, slow-moving stock) because definitions are taught to the AI once.

## 2. How it works (architecture)

```
 User question (VI / EN)
        |
        v
 +-------------+     +--------------------------------------+
 | Streamlit UI|---->| agent.py  (role logic, orchestration)|
 +-------------+     +--------------------------------------+
        ^                 |                        |
        |                 v                        v
        |       +------------------+      +------------------+
        |       | Vanna RAG        |      | Gemini (LLM)     |
        |       | ChromaDB vectors |----->| writes SQL, then |
        |       | DDL + KPI docs + |      | explains result  |
        |       | example Q->SQL   |      +------------------+
        |       +------------------+
        |                 | generated SQL
        |                 v
        |       +------------------+   blocks anything that is not a
        |       | sql_guard.py     |   single SELECT on allowed tables
        |       +------------------+
        |                 | safe SQL
        |                 v
        |       +------------------+
        +-------| SQLite (opened   |  -> DataFrame -> table + chart
                |  read-only)      |
                +------------------+
```

**Step by step**
1. **Retrieve (RAG):** Vanna embeds the question and fetches the most relevant table definitions, KPI definitions and similar solved examples from ChromaDB.
2. **Generate:** Gemini receives the question plus that retrieved context and writes a SQL query. Grounding in company-specific context is what makes it accurate; the model is not guessing the schema.
3. **Validate:** `backend/sql_guard.py` checks the SQL before execution.
4. **Execute:** the query runs on a database connection opened in read-only mode.
5. **Explain:** the top rows go back to Gemini, which writes a short answer in the selected role's voice. The UI shows table, chart, and an expandable "View SQL" panel for transparency.

**Training data for RAG** (`training/knowledge.py`): table DDL, 10 business definitions (e.g. *Revenue = SUM(quantityOrdered x priceEach) excluding cancelled orders*), and 17 question-SQL pairs in both languages. The knowledge base builds itself on first start.

## 3. Security measures

| Layer | Control |
|---|---|
| Database access | SQLite file opened with `mode=ro` (`backend/db.py`): the engine itself rejects any write. In a server database this maps to a dedicated `GRANT SELECT`-only user |
| Query validation | Only a **single SELECT / WITH** statement; rejects INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, ATTACH, multiple statements; comments are stripped first |
| Table whitelist | Only the 8 business tables can be read (`ALLOWED_TABLES` in `config.py`). Enforced twice: by the SQL guard and again by a SQLite **authorizer** in `backend/db.py`, so comma-joins, quoted names or system tables (`sqlite_master`) cannot get around it |
| Secrets | API key and DB password come from environment variables / `.env` (git-ignored), nothing is hard-coded |
| Role scope | CEO role limited to revenue and sales-rep questions; Technical Mentor never queries data |
| Transparency | Every generated SQL is visible to the user |

Defence in depth: even if the code validation were bypassed, the read-only connection cannot write.

## 4. Current limitations (honest list)

- **Not production-grade authorization:** roles are a UI/prompt-level feature. A real deployment must map them to the company's real users, groups and row-level permissions.
- **Regex-based SQL guard:** good for a demo; production should parse SQL with a real parser (e.g. sqlglot) and enforce row/column-level policies.
- **LLM accuracy:** text-to-SQL can be wrong on ambiguous questions. Mitigation: the SQL is shown, and more verified Q-SQL pairs improve it.
- **Data leaves the premises:** the top 10 result rows are sent to Gemini to write the explanation. Sensitive data would need a self-hosted model or masking.
- **Sample data only:** the classicmodels dataset (2003-2005) is not a full ERP: no suppliers, warehouses or stock movements.
- **Role keyword filter** for the CEO is simple string matching, not intent classification.
- Answer caching is in-memory only (lost on restart); no rate limiting or audit log yet.
- **Free-tier quota:** the demo relies on Gemini's free tier, so heavy use can hit daily limits (the app falls back across keys/models and shows a friendly message).

## 5. Taking it toward production

1. **Data layer:** point the assistant at a **read-only replica** of the real operational database (e.g. PostgreSQL), exposing only curated tables or views.
2. **Knowledge layer:** retrain Vanna with that schema, the company's own KPI definitions, and validated question-SQL pairs (a business-owned, reviewable asset in `training/knowledge.py`).
3. **Service layer:** wrap the pipeline behind a small REST API, or an **MCP server** exposing `ask_data(question)` as a tool so any AI agent can call it.
4. **Identity and permissions:** pass the end user's identity through and restrict queries to what that user may see (row- and column-level policies).
5. **Governance:** audit log of questions and SQL, approval workflow for new KPI definitions, and an evaluation set of questions to measure accuracy before each release.

## 6. Run locally

**Prerequisites:** Python 3.10+ and a free [Gemini API key](https://aistudio.google.com/). No database server needed: the sample data ships as a SQLite file.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then paste your key into GEMINI_API_KEY
streamlit run frontend/app.py
```

On first start the app builds its knowledge base (about a minute; it downloads a small local embedding model). To rebuild after editing `training/knowledge.py`: `python training/train.py`. To regenerate the database from the original MySQL dump: `python scripts/build_sqlite.py`.

Example questions: *Top 5 sản phẩm bán chạy nhất?*, *Revenue by product line*, *Which products have the highest stock but sell the least?*

## 7. Deploy for free (Streamlit Community Cloud)

1. Push this repo to GitHub (`.env` and `chroma_store/` are git-ignored; `data/classicmodels.db` is committed).
2. Go to [share.streamlit.io](https://share.streamlit.io), click **New app**, select the repo, branch `main`, main file `frontend/app.py`.
3. Open **Advanced settings > Secrets** and add:
   ```toml
   GEMINI_API_KEY = "your-key"
   ```
4. Deploy. The first load builds the knowledge base; later loads are instant.

Tip: set a quota alert on the Gemini key, since a public demo spends your free-tier quota.

## 8. Project structure

```
backend/
  agent.py          orchestration: role logic, SQL -> run -> explain
  sql_guard.py      SELECT-only and table whitelist validation
  db.py             read-only SQLite access
  llm_client.py     Gemini wrapper (key fallback on quota errors)
  vanna_setup.py    Vanna + ChromaDB wiring, auto-training on first start
frontend/           Streamlit UI and chart helpers
prompt/             role prompts (CEO, Head of Sales, Technical Mentor)
training/           knowledge.py (KPI definitions + Q-SQL pairs), train.py (rebuild)
data/               classicmodels.db (sample ERP-style data)
scripts/            build_sqlite.py (MySQL dump -> SQLite)
config.py           settings from environment variables
```

## 9. Tech stack

Python, Vanna (RAG for text-to-SQL), ChromaDB, Google Gemini, SQLite, Streamlit, Plotly.
