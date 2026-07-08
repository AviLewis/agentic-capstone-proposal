# coResearcher backend

FastAPI + LangGraph service that powers the coResearcher multi-agent research
planning pipeline (ideate -> literature review -> methodology -> plan -> judge).

## Quickstart

```bash
cd backend
python3.14 -m venv .venv   # Python 3.11+ required (LangGraph async interrupts)
source .venv/bin/activate
pip install -e ".[dev]"

# Copy env and fill in secrets (see repo root .env.example)
cp ../.env.example ../.env

uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000/health to verify the service is up.

## Layout

- `app/config.py` - central `Settings` loader (pydantic-settings), fails fast on
  missing required secrets.
- `app/graph/` - LangGraph orchestrator + agent nodes.
- `app/tools/` - literature search tools (OpenAlex, arXiv, Semantic Scholar).
- `app/notion/` - Notion MCP client for exporting approved plans.
- `app/db/` - Supabase/Postgres access layer + checkpointer wiring.
- `tests/` - unit + integration tests.
