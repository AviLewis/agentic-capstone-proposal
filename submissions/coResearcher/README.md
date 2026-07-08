# coResearcher

A multi-agent research assistant that turns a researcher's brief into ranked,
feasible research plans. A LangGraph pipeline runs
**ideate -> literature review -> methodology -> research plan -> judge**, with
human-in-the-loop gates, Supabase persistence, and Notion export via MCP.

> Status: **Phases 0–6 complete.** Data layer, LangGraph pipeline, agents,
> literature tools, REST/SSE API, Notion export, and the streaming Next.js UI
> are all implemented.

## Architecture

```
Next.js UI  --POST brief / SSE-->  FastAPI  -->  LangGraph orchestrator
                                                   |
   Ideator -> [HITL: pick questions] -> Literature review (plan/act/observe)
     -> Methodology -> Research plan -> Judge (rubric scoring + rank)
                                                   |
   OpenAlex / arXiv / Semantic Scholar        Supabase (Postgres: data + checkpoints)
                                                   |
                              [HITL: approve plan] -> Notion export (MCP)
```

The system has three cooperating layers:

- **Frontend (`frontend/`)** — a Next.js App Router UI that submits a brief,
  subscribes to a live Server-Sent Events (SSE) stream, renders the two
  human-in-the-loop (HITL) gates, and displays ranked results.
- **Backend (`backend/`)** — a FastAPI service that owns a **LangGraph**
  orchestrator. The graph runs five LLM agents in sequence, calls external
  literature APIs, persists everything to Postgres, and pauses at two HITL gates
  using LangGraph's `interrupt()` + Postgres checkpointing.
- **Data & integrations** — **Supabase Postgres** stores both the domain data
  and the LangGraph checkpoints; **OpenAlex / arXiv / Semantic Scholar** provide
  the literature; **Notion** (via an MCP subprocess) is the export target.

## Repo layout

| Path         | Purpose                                                        |
| ------------ | ------------------------------------------------------------- |
| `backend/`   | FastAPI app, LangGraph nodes, tools, Notion MCP client, DB.    |
| `frontend/`  | Next.js (App Router, TS, Tailwind, shadcn/ui) streaming UI.    |
| `supabase/`  | SQL migrations for domain tables + RLS.                        |
| `.env.example` | All environment variables (copy to `.env`).                 |

## Agent architecture

The heart of coResearcher is a **LangGraph `StateGraph`** defined in
`backend/app/graph/graph.py`. It threads a single `ResearchState`
(`backend/app/graph/state.py`) through processing nodes and two interrupt gates:

```
START -> ideator -> [gate: pick questions] -> literature_review
      -> methodology -> research_plan -> judge -> [gate: approve plan] -> END
```

Responsibilities are split across layers so the LLM logic stays pure and
testable:

| Layer            | Location                       | Role                                                             |
| ---------------- | ------------------------------ | --------------------------------------------------------------- |
| Graph nodes      | `backend/app/graph/nodes.py`   | Wire agents to state, persist to DB, enforce budgets, run gates. |
| Agents           | `backend/app/agents/*.py`      | Pure async LLM logic: prompts + structured (Pydantic) output.   |
| LLM helper       | `backend/app/llm.py`           | `ainvoke_structured()` — OpenAI call + parsing + cost tracking. |
| Injectable deps  | `backend/app/graph/deps.py`    | `invoke` / `search` are overridable (real vs. test doubles).    |
| Tools            | `backend/app/tools/`           | Literature search over OpenAlex, arXiv, Semantic Scholar.       |
| Guards           | `backend/app/graph/guards.py`  | Budget caps + prompt-injection wrapping of untrusted text.      |
| Execution        | `backend/app/run_manager.py`   | Background `astream`, pub/sub that feeds the SSE stream.         |
| Checkpointing    | `backend/app/db/checkpointer.py` | Postgres saver enabling pause/resume across HITL gates.       |

### The five agents

1. **Ideator** (`agents/ideator.py`) — turns the brief, researcher context, and
   any "own data" into a diverse set of candidate research questions (each with a
   rationale and tag). Runs hot (temperature ~0.9) for breadth.
2. **Literature review** (`agents/literature.py`) — a **plan → act → observe**
   loop per selected question: the LLM drafts 2–4 search queries, calls
   `search_all()` against OpenAlex + arXiv, assesses coverage, optionally refines
   (up to 2 iterations), then selects the most relevant papers. External
   abstracts are wrapped in `<untrusted_data>` blocks to blunt prompt injection.
3. **Methodology** (`agents/methodology.py`) — synthesizes candidate methods,
   datasets, and gaps from the selected papers and the researcher's own data.
4. **Research plan** (`agents/plan.py`) — drafts a structured plan per question:
   objective, hypotheses, methods, data, risks, and resources.
5. **Judge** (`agents/judge.py`) — scores each plan 1–5 against a weighted
   feasibility rubric (`FEASIBILITY_RUBRIC` in `state.py`) and ranks them:
   data availability (0.25), methodological soundness (0.25), scope/time realism
   (0.20), novelty (0.15), resource/skill fit (0.15).

Every agent calls the injectable `invoke` (defaulting to `ainvoke_structured`),
which uses `ChatOpenAI.with_structured_output(...)` and accumulates token counts
and estimated USD cost into the graph state so caps can be enforced live.

### Human-in-the-loop gates

Both gates use LangGraph `interrupt()` in `nodes.py`; the run's checkpoint is
saved to Postgres so it can resume exactly where it paused after a client
responds via `POST /runs/{id}/resume`.

| Gate                | Interrupt payload                              | Resume payload                                                   |
| ------------------- | ---------------------------------------------- | --------------------------------------------------------------- |
| Question selection  | `{ gate: "question_selection", questions }`    | `{ selected_indexes: [...] }` / `{ selected_ids: [...] }`, opt. `edits` |
| Plan approval       | `{ gate: "plan_approval", ranked_plans }`      | `{ approved_index: 0 }` / `{ approved_plan_id: "..." }`          |

### Budget guards

Each processing node checks caps first (`graph/guards.py`); on breach it sets the
run `status` to `capped` and routes straight to `END`. Defaults (from `Caps` in
`state.py`, overridable per run via the `POST /runs` `caps` field):

| Cap                       | Default   |
| ------------------------- | --------- |
| `max_questions`           | 6         |
| `max_papers_per_question` | 8         |
| `max_tool_calls`          | 40        |
| `token_ceiling`           | 400,000   |
| `cost_ceiling_usd`        | $5.00     |
| `wall_clock_seconds`      | 900 (15m) |

### Run lifecycle (status)

`pending -> ideating -> awaiting_question_selection -> reviewing_literature ->
designing_methodology -> planning -> judging -> awaiting_plan_approval ->
completed` (or `capped` / `error`). Statuses live in `backend/app/enums.py`.

## How it works end-to-end

1. **Create run** — `BriefForm` posts the brief to `POST /runs`. The backend
   inserts `projects` + `runs` rows, builds the initial `ResearchState`, and
   starts the graph in a background task via `RunManager.start()`. It returns the
   `run_id` / `thread_id` and the UI navigates to `/runs/{id}`.
2. **Stream progress** — the UI opens an `EventSource` on `/runs/{id}/stream`.
   As each node completes, `RunManager` publishes `node` and `cost` SSE events.
3. **Gate 1 (questions)** — the graph pauses at `gate_questions` and emits an
   `interrupt` event. The user picks questions in `QuestionGate`, which calls
   `POST /runs/{id}/resume`; the graph resumes from its checkpoint and the UI
   reconnects the SSE stream.
4. **Processing** — literature review (with counted tool calls), methodology,
   plan drafting, and judging each persist to Postgres and emit SSE updates.
5. **Gate 2 (plan approval)** — the graph pauses at `gate_plan_approval`. The
   user approves one ranked plan in `PlanApprovalGate` and resumes the run.
6. **Completion** — an SSE `completed` event fires; `RunView` fetches
   `GET /runs/{id}` for the full persisted results (questions, papers,
   methodology, plans, scores).
7. **Export** — clicking **Export to Notion** calls `POST /runs/{id}/export`,
   which verifies an approved plan, renders it to Notion blocks, creates the page
   through the Notion MCP subprocess, and stores the URL on `plans.notion_url`.

## Data model

Supabase Postgres holds the domain tables (`supabase/migrations/0001_init.sql`)
plus LangGraph's checkpoint tables (created at runtime on startup):

```
projects (1) --< runs (1) --< questions (1) --< papers
                                   |
                                   +-- methodologies (1:1)
                                   +-- plans (1) --< scores
```

Every table has a `uuid` primary key (`id`, default `gen_random_uuid()`) and a
`created_at timestamptz`. Tables that are updated in place also carry an
`updated_at timestamptz` maintained by a trigger. All foreign keys cascade on
delete, so removing a project tears down its entire tree.

### `projects` — the researcher's brief

| Column               | Type          | Description                                        |
| -------------------- | ------------- | -------------------------------------------------- |
| `brief`              | `text`        | The research brief. **Required.**                  |
| `researcher_context` | `text`        | Optional background about the researcher/domain.   |
| `own_data`           | `text`        | Optional description of data/constraints they have. |
| `created_at` / `updated_at` | `timestamptz` | Timestamps.                                  |

### `runs` — one graph execution for a project

| Column       | Type          | Description                                                          |
| ------------ | ------------- | ------------------------------------------------------------------- |
| `project_id` | `uuid` FK     | Parent project (cascade delete). Indexed.                           |
| `thread_id`  | `text` unique | LangGraph thread id (maps the run to its checkpoints).              |
| `status`     | `text` enum   | Lifecycle state (see run lifecycle above); CHECK-constrained.       |
| `caps`       | `jsonb`       | Budget/limits for the run (question/paper/tool/token/cost/time caps). |
| `cost_used`  | `jsonb`       | Accumulated tokens, USD cost, and tool-call counts.                 |
| `error`      | `text`        | Error message when `status = 'error'`.                              |
| `created_at` / `updated_at` | `timestamptz` | Timestamps.                                          |

### `questions` — candidate research questions (from the Ideator)

| Column      | Type      | Description                                                    |
| ----------- | --------- | ------------------------------------------------------------- |
| `run_id`    | `uuid` FK | Parent run (cascade delete). Indexed.                         |
| `text`      | `text`    | The question. **Required.**                                   |
| `rationale` | `text`    | Why the question is worth pursuing.                           |
| `tag`       | `text`    | Novelty/scope tag.                                            |
| `selected`  | `boolean` | Whether the user picked it at Gate 1 (default `false`). Indexed with `run_id`. |
| `position`  | `integer` | Display order (default `0`).                                  |

### `papers` — literature surfaced per question

Deduped by DOI / normalized title during literature review.

| Column        | Type      | Description                                                  |
| ------------- | --------- | ----------------------------------------------------------- |
| `question_id` | `uuid` FK | Parent question (cascade delete). Indexed.                  |
| `source`      | `text`    | `openalex` \| `arxiv` \| `semantic_scholar`. **Required.**  |
| `title`       | `text`    | Paper title. **Required.**                                  |
| `authors`     | `jsonb`   | Array of author names (default `[]`).                       |
| `year`        | `integer` | Publication year.                                           |
| `venue`       | `text`    | Journal/conference.                                         |
| `doi`         | `text`    | DOI (indexed for dedupe).                                   |
| `url`         | `text`    | Link to the paper.                                          |
| `abstract`    | `text`    | Abstract (treated as untrusted input).                     |
| `relevance`   | `text`    | LLM-generated relevance rationale.                         |

### `methodologies` — one synthesis per question (1:1)

| Column        | Type      | Description                                              |
| ------------- | --------- | ------------------------------------------------------- |
| `question_id` | `uuid` FK | Parent question — **unique** (one per question). Indexed. |
| `methods`     | `jsonb`   | Array of candidate methods (default `[]`).             |
| `datasets`    | `jsonb`   | Array of candidate datasets (default `[]`).            |
| `gaps`        | `jsonb`   | Array of identified research gaps (default `[]`).      |
| `created_at` / `updated_at` | `timestamptz` | Timestamps.                             |

### `plans` — structured research plan per question

| Column              | Type      | Description                                                        |
| ------------------- | --------- | ----------------------------------------------------------------- |
| `question_id`       | `uuid` FK | Parent question (cascade delete). Indexed.                        |
| `content_json`      | `jsonb`   | Full plan: objective, hypotheses, methods, data, risks, resources. **Required.** |
| `feasibility_total` | `numeric` | Weighted judge score.                                             |
| `rank`              | `integer` | Ranking among plans (`1` = most feasible).                        |
| `notion_url`        | `text`    | Set after a successful Notion export.                             |
| `created_at` / `updated_at` | `timestamptz` | Timestamps.                                        |

### `scores` — per-criterion judge scores for a plan

Unique per `(plan_id, criterion)`.

| Column          | Type      | Description                                                   |
| --------------- | --------- | ----------------------------------------------------------- |
| `plan_id`       | `uuid` FK | Parent plan (cascade delete). Indexed.                      |
| `criterion`     | `text`    | Rubric criterion (e.g. `data_availability`). **Required.**  |
| `score`         | `numeric` | Score 1–5 for the criterion. **Required.**                 |
| `weight`        | `numeric` | Rubric weight for the criterion. **Required.**             |
| `justification` | `text`    | Rationale for the score.                                    |
| `total`         | `numeric` | Plan's weighted total (denormalized onto each row).        |

Row Level Security is enabled on every table with **no permissive policies**, so
only the service-role backend can read/write. The backend connects directly with
`psycopg` using `SUPABASE_DB_URL`.

## Prerequisites

- Python 3.11+ (3.14 recommended; required for LangGraph async HITL `interrupt()`)
- Node.js 18+ (frontend)
- A Supabase project (Postgres) and an OpenAI API key

## Setup

1. Copy env and fill in secrets:

```bash
cp .env.example .env
```

2. Database (Supabase Postgres) — apply the schema migration:

```bash
psql "$SUPABASE_DB_URL" -f supabase/migrations/0001_init.sql
```

The backend also creates LangGraph checkpoint tables automatically on startup.

3. Backend:

```bash
cd backend
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
# Verify: http://localhost:8000/health
```

4. Frontend:

```bash
cd frontend
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL (default http://localhost:8000)
npm install
npm run dev
# Verify: http://localhost:3000
```

### UI flow

1. `/` — submit a research brief (with optional context, own data, and advanced
   caps). Creating a run navigates to `/runs/{id}`.
2. `/runs/{id}` — a live timeline streams node progress and running cost over SSE.
3. **Gate 1** — pick which generated questions proceed; submitting resumes the run.
4. **Gate 2** — review ranked plans with per-criterion feasibility scores and
   approve one.
5. Results — full ranked plans, papers, and methodology per question, each with a
   one-click **Export to Notion** button.

## Environment variables

See [`.env.example`](./.env.example). Required backend secrets: `OPENAI_API_KEY`,
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_DB_URL`. Optional: `NOTION_TOKEN`,
`CONTACT_EMAIL` (OpenAlex polite pool), `SEMANTIC_SCHOLAR_API_KEY`.

## API

| Method | Path                  | Purpose                                                   |
| ------ | --------------------- | -------------------------------------------------------- |
| POST   | `/runs`               | Create project + run, start the graph, return ids.       |
| GET    | `/runs/{id}/stream`   | SSE stream: `snapshot`, `node`, `cost`, `interrupt`, `completed`, `error`. |
| POST   | `/runs/{id}/resume`   | Resume after a HITL gate (question selection / approval).  |
| POST   | `/runs/{id}/export`   | Export the approved plan to Notion via MCP (returns page URL). |
| GET    | `/runs/{id}`          | Fetch full results (questions, papers, plans, scores).    |
| GET    | `/health`, `/ready`   | Liveness / readiness (incl. DB status).                   |

Resume payloads: `{"resume": {"selected_indexes": [0,1]}}` (or `selected_ids`,
optional `edits`) for question selection; `{"resume": {"approved_index": 0}}` (or
`approved_plan_id`) for plan approval. Errors use a consistent envelope:
`{"error": {"code", "message", "details?"}}`.

## Development

```bash
# Backend tests + lint
cd backend
pytest
ruff check .
```
