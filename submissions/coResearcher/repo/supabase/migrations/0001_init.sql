-- coResearcher initial schema
-- Domain tables for the multi-agent research pipeline:
--   projects -> runs -> questions -> {papers, methodologies, plans -> scores}
--
-- LangGraph checkpoint tables are created separately at runtime by the
-- AsyncPostgresSaver (see backend/app/db/checkpointer.py).
--
-- Security model: RLS is enabled on every table with NO permissive policies,
-- so all access is denied by default. The backend connects with the Supabase
-- service role, which bypasses RLS. Never expose the service key to clients.

begin;

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- updated_at trigger helper
-- ---------------------------------------------------------------------------
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- projects: a researcher's brief + context + their own data/constraints
-- ---------------------------------------------------------------------------
create table if not exists projects (
  id                  uuid primary key default gen_random_uuid(),
  brief               text not null,
  researcher_context  text,
  own_data            text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create trigger projects_set_updated_at
  before update on projects
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- runs: one execution of the graph for a project (maps to a LangGraph thread)
-- ---------------------------------------------------------------------------
create table if not exists runs (
  id           uuid primary key default gen_random_uuid(),
  project_id   uuid not null references projects (id) on delete cascade,
  thread_id    text not null unique,
  status       text not null default 'pending'
    check (status in (
      'pending',
      'ideating',
      'awaiting_question_selection',
      'reviewing_literature',
      'designing_methodology',
      'planning',
      'judging',
      'awaiting_plan_approval',
      'completed',
      'capped',
      'error'
    )),
  caps         jsonb not null default '{}'::jsonb,   -- budget/limits for the run
  cost_used    jsonb not null default '{}'::jsonb,   -- accumulated tokens/cost/tool calls
  error        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists runs_project_id_idx on runs (project_id);

create trigger runs_set_updated_at
  before update on runs
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- questions: candidate research questions produced by the Ideator
-- ---------------------------------------------------------------------------
create table if not exists questions (
  id          uuid primary key default gen_random_uuid(),
  run_id      uuid not null references runs (id) on delete cascade,
  text        text not null,
  rationale   text,
  tag         text,                                  -- novelty/scope tag
  selected    boolean not null default false,
  position    integer not null default 0,
  created_at  timestamptz not null default now()
);

create index if not exists questions_run_id_idx on questions (run_id);
create index if not exists questions_selected_idx on questions (run_id, selected);

-- ---------------------------------------------------------------------------
-- papers: literature surfaced per question (deduped by DOI/normalized title)
-- ---------------------------------------------------------------------------
create table if not exists papers (
  id           uuid primary key default gen_random_uuid(),
  question_id  uuid not null references questions (id) on delete cascade,
  source       text not null,                        -- openalex | arxiv | semantic_scholar
  title        text not null,
  authors      jsonb not null default '[]'::jsonb,   -- array of author names
  year         integer,
  venue        text,
  doi          text,
  url          text,
  abstract     text,
  relevance    text,                                 -- LLM relevance rationale
  created_at   timestamptz not null default now()
);

create index if not exists papers_question_id_idx on papers (question_id);
create index if not exists papers_doi_idx on papers (doi);

-- ---------------------------------------------------------------------------
-- methodologies: one methodology synthesis per question
-- ---------------------------------------------------------------------------
create table if not exists methodologies (
  id           uuid primary key default gen_random_uuid(),
  question_id  uuid not null unique references questions (id) on delete cascade,
  methods      jsonb not null default '[]'::jsonb,
  datasets     jsonb not null default '[]'::jsonb,
  gaps         jsonb not null default '[]'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists methodologies_question_id_idx on methodologies (question_id);

create trigger methodologies_set_updated_at
  before update on methodologies
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- plans: structured research plan per question + ranking/scoring rollup
-- ---------------------------------------------------------------------------
create table if not exists plans (
  id                uuid primary key default gen_random_uuid(),
  question_id       uuid not null references questions (id) on delete cascade,
  content_json      jsonb not null,                  -- objective, hypotheses, methods, ...
  feasibility_total numeric,                          -- weighted judge score
  rank              integer,                           -- 1 = most feasible
  notion_url        text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists plans_question_id_idx on plans (question_id);

create trigger plans_set_updated_at
  before update on plans
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- scores: per-criterion judge scores for a plan
-- ---------------------------------------------------------------------------
create table if not exists scores (
  id             uuid primary key default gen_random_uuid(),
  plan_id        uuid not null references plans (id) on delete cascade,
  criterion      text not null,
  score          numeric not null,
  weight         numeric not null,
  justification  text,
  total          numeric,                             -- plan weighted total (denormalized)
  created_at     timestamptz not null default now()
);

create index if not exists scores_plan_id_idx on scores (plan_id);
create unique index if not exists scores_plan_criterion_idx on scores (plan_id, criterion);

-- ---------------------------------------------------------------------------
-- Row Level Security: deny by default; only the service role (which bypasses
-- RLS) may read/write. This keeps all writes server-side.
-- ---------------------------------------------------------------------------
alter table projects       enable row level security;
alter table runs           enable row level security;
alter table questions      enable row level security;
alter table papers         enable row level security;
alter table methodologies  enable row level security;
alter table plans          enable row level security;
alter table scores         enable row level security;

commit;
