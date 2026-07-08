# Supabase

SQL migrations for coResearcher domain tables (`projects`, `runs`, `questions`,
`papers`, `methodologies`, `plans`, `scores`) with RLS. LangGraph checkpoint
tables are created at runtime by `AsyncPostgresSaver` (see
`backend/app/db/checkpointer.py`).

## Migrations

- `migrations/0001_init.sql` — domain schema: tables, FKs (all `on delete
  cascade`), indexes, a `status` check constraint on `runs`, `caps` / `cost_used`
  JSONB columns, `updated_at` triggers, and RLS enabled on every table.

### Security model

RLS is **enabled with no permissive policies**, so all access is denied by
default. The backend connects with the Supabase **service role**, which bypasses
RLS — keeping every write server-side. Never expose the service key to clients.

## Applying migrations

Using `psql` against `SUPABASE_DB_URL`:

```bash
psql "$SUPABASE_DB_URL" -f supabase/migrations/0001_init.sql
```

Or with the Supabase CLI (if you manage the project locally):

```bash
supabase db push
```

The migration is written to be safe to re-run (`create table if not exists`,
`create index if not exists`).
