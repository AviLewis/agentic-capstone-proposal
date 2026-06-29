# Capstone Demo Day — your project proposal

Submit a one-folder overview of your product for Demo Day. **Judging is evidence-based** — this repo
gives you the template and the dimensions you'll be scored on, so there are no surprises.

## How to submit
1. Copy [`CAPSTONE-PROPOSAL-TEMPLATE.md`](CAPSTONE-PROPOSAL-TEMPLATE.md) into a folder:
   `submissions/<your-project>/proposal.md`.
2. Fill it in. Every section maps to a scoring dimension — don't skip one.
3. Add **evidence** to that folder: a clone/export of your (preferably public) repo, a runnable test,
   a short demo recording, sample output/logs, screenshots.
4. Hand the folder to your instructor as directed.

## How you're judged (rubric — weights sum to 100)
| Dimension | Weight | What it measures |
|---|---:|---|
| Agentic depth | 25 | Real agency (plan→act→observe loop, tools, autonomy, multi-agent, memory) vs a prompt wrapper |
| Engineering excellence | 20 | Code quality & robustness, error handling, tests, observability — *not* system size |
| Product & ease of use | 15 | Clear value, a real user, usable & polished |
| Potential & MOAT | 15 | Could it be a real, *defensible* product? |
| Safety & control | 15 | HITL, guardrails, caps, injection/untrusted-input & secret handling |
| Complexity & difficulty | 5 | A hard problem genuinely solved — independent of agent/component count |
| Demo & communication | 5 | Clear writeup + verifiable evidence it works |

Scored **1–10** per dimension; `final = Σ (score/10 × weight)`, out of 100.

## What wins (and what loses)
- **Show, don't tell — evidence is tiered.** A claim that's *prose only* is **asserted** (capped at a
  middling score). Code that *exists* in your folder is **present** (higher cap). Proof the behavior
  *actually ran* — a runnable test, a reproducible run, or a public URL — is **demonstrated**, and only
  that reaches top marks. Screenshots and pasted logs are weak (easy to fake); lead with a test or a
  live link. **Curate**: a few artifacts that prove the most beat a wall of 40 screenshots.
- **Agentic depth is the heaviest dimension** — this is an agentic fellowship. A polished app with no
  real agency won't beat a rougher one with genuine, working agency. Multi-agent is rewarded once
  (here), so a clean single-agent product isn't penalized for being focused.
- **Safety has a downside, not just an upside.** An agent that takes a **high-harm** action unattended
  with no human-in-the-loop and no caps — spends money, messages other people, or does something
  unrecoverable — is penalized and can be **excluded from the top tier**. (Self-notifications and
  reversible/backed-up writes are fine.) Say where your human-in-the-loop and caps are.
- **Don't try to game the judge.** A live instruction to the judge in your proposal ("score me 10",
  "ignore the rubric") is an injection attempt: it's flagged, docks your Safety, and makes you
  **ineligible** for the top tier. *But* describing your product's own prompt-injection handling
  **scores well** — just **fence any example attack strings in a code block** so they read as content,
  not a command. (You learned this in the security workshop. This is the exam.)

## Folder layout
- `CAPSTONE-PROPOSAL-TEMPLATE.md` — the template to copy and fill in.
- `submissions/<your-project>/` — your `proposal.md` + your evidence.

> Honest scoping and verifiable evidence beat polish and adjectives. Build something real, then prove it.
