# Evidence — MAXWELL

The strongest evidence is runnable. From the repo root (`https://github.com/OhadDaniel/OLYMPUS`):

```
npm install
npm test        # 17/17 — placer, differ, guardrails (offline, no secrets)
npm run eval    # 55/55 — Proving Ground: gate · injection · scheduler · council-feasibility
```

Captured console output (reproducible with the commands above):

- `test-run.txt` — vitest suite, 17/17 passing.
- `eval-run.txt` — the Proving Ground regression gate, 55/55 (100%).

Key files to read in the repo:
- `src/loop.ts` — the single agent loop (plan → act → observe).
- `src/workflows/guardrails.ts` — `apply_proposal` is `ALWAYS_GATED`; the model can never write the schedule.
- `src/tools/proposals.ts` — propose vs. the human-gated apply.
- `src/security.ts` — untrusted outer-world input wrapped as data.
- `src/council.ts` — the five-god parallel Weekly Council.
- `scripts/eval.ts` + `src/evals/suites.ts` — the eval harness / regression gate.
