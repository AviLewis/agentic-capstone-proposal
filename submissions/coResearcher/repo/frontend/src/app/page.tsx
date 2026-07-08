import type { Metadata } from "next";
import Link from "next/link";
import { LandingPipeline } from "@/components/landing-pipeline";
import { LandingAmbientBackground } from "@/components/landing-ambient-background";

export const metadata: Metadata = {
  title: "coResearcher",
  description:
    "A one-line brief in. Ranked, feasible research plans out — five specialist agents ideate, review literature, design methods, plan, and judge.",
};

const ACCENT = "#e8b04b";
const GLOW_TINT = "rgba(232, 176, 75, 0.16)";

const SOURCES = [
  { name: "OpenAlex", note: "250M+ scholarly works, open metadata & citations." },
  { name: "arXiv", note: "Preprints across physics, CS, quant bio & more." },
  { name: "Semantic Scholar", note: "AI-ranked relevance and influence signals." },
  { name: "Notion", note: "One-click export of the approved plan via MCP." },
];

const SAMPLE_FIELDS = [
  { label: "DESIGN", value: "Within-subject crossover, 2 sleep conditions × chronotype" },
  { label: "MEASURES", value: "Word-pair recall, EEG spindle density, actigraphy" },
  { label: "EVIDENCE", value: "16 papers cited across 2 questions" },
  { label: "TIMELINE", value: "14 weeks · n≈48" },
];

const RUBRIC = [
  { label: "Novelty", score: "4.5", pct: "90%" },
  { label: "Feasibility", score: "4.2", pct: "84%" },
  { label: "Evidence base", score: "4.6", pct: "92%" },
  { label: "Impact", score: "4.0", pct: "80%" },
];

export default function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#131519] text-[#e8e6e1]">
      <LandingAmbientBackground glowTint={GLOW_TINT} />

      <nav className="relative z-[5] mx-auto flex max-w-[1180px] items-center justify-between px-6 py-[22px] sm:px-8">
        <span className="font-mono text-[15px] font-bold tracking-[0.01em] text-[#e8b04b]">
          co·researcher
        </span>
        <div className="font-mono flex items-center gap-5 text-xs sm:gap-7">
          <a href="#how" className="hidden text-[#8b909c] sm:inline">
            how it works
          </a>
          <a href="#sources" className="hidden text-[#8b909c] sm:inline">
            sources
          </a>
          <a href="#sample" className="hidden text-[#8b909c] sm:inline">
            sample
          </a>
          <Link
            href="/new"
            className="rounded-md bg-[#e8b04b] px-4 py-2 font-semibold text-[#16181d]"
          >
            Start a research run
          </Link>
        </div>
      </nav>

      <header className="relative z-[2] mx-auto max-w-[940px] px-6 pt-14 pb-8 text-center sm:px-8">
        <div className="font-mono mb-[30px] inline-flex items-center gap-[9px] rounded-full border border-[#2a2d35] px-3.5 py-1.5 text-[11px] tracking-[0.16em] text-[#8b909c]">
          <span
            className="h-1.5 w-1.5 rounded-full bg-[#4ec97a]"
            style={{ boxShadow: "0 0 8px #4ec97a" }}
          />
          MULTI-AGENT RESEARCH PLANNING
        </div>
        <h1 className="mx-auto max-w-[16ch] text-[40px] leading-[1.1] font-bold tracking-[-0.02em] text-[#f3f1ec] sm:text-[52px] lg:text-[66px] lg:leading-[1.04]">
          A one-line brief in. <span style={{ color: ACCENT }}>Ranked, feasible plans</span> out.
        </h1>
        <p className="mx-auto mt-[26px] max-w-[56ch] text-[17px] leading-[1.55] text-[#c6c4bf] sm:text-[19px]">
          Five specialist agents ideate questions, review the live literature,
          design methods, draft plans, and rank them by feasibility — with
          you in the loop at every gate.
        </p>

        <div className="mt-9 flex flex-wrap justify-center gap-3.5">
          <Link
            href="/new"
            className="font-mono inline-flex items-center gap-[9px] rounded-lg px-6 py-3.5 text-sm font-semibold text-[#16181d]"
            style={{ background: ACCENT, boxShadow: `0 8px 30px ${GLOW_TINT}` }}
          >
            Start a research run <span className="text-[15px]">→</span>
          </Link>
          <a
            href="#sample"
            className="font-mono inline-flex items-center gap-[9px] rounded-lg border border-[#2a2d35] bg-[#1a1d23] px-[22px] py-3.5 text-sm font-medium text-[#e8e6e1]"
          >
            See a sample plan
          </a>
        </div>
      </header>

      <section id="how" className="relative z-[2] mx-auto mt-11 max-w-[1060px] px-6 pb-5 sm:px-10">
        <LandingPipeline />
        <p className="font-mono mt-5 text-center text-xs text-[#6d7280]">
          5 agents · 3 literature sources · 2 human-in-the-loop gates · full
          audit trail
        </p>
      </section>

      <section id="sources" className="relative z-[2] mx-auto mt-[72px] max-w-[1060px] px-6 sm:px-10">
        <p className="font-mono mb-[26px] text-center text-[11px] tracking-[0.16em] text-[#6d7280]">
          SEARCHES THE LIVE LITERATURE ACROSS
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {SOURCES.map((src) => (
            <div
              key={src.name}
              className="flex flex-col gap-2 rounded-xl border border-[#2a2d35] bg-[#1a1d23] px-5 py-[22px]"
            >
              <span className="font-mono text-[15px] font-bold text-[#e8e6e1]">
                {src.name}
              </span>
              <span className="text-[12.5px] leading-[1.45] text-[#8b909c]">
                {src.note}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section id="sample" className="relative z-[2] mx-auto mt-20 max-w-[1060px] px-6 sm:px-10">
        <div className="mb-[34px] text-center">
          <p className="font-mono mb-3 text-[11px] tracking-[0.16em] text-[#8b909c]">
            THE PAYOFF
          </p>
          <h2 className="text-[28px] font-bold tracking-[-0.02em] text-[#f3f1ec] sm:text-[38px]">
            Every run ends with ranked, defensible plans.
          </h2>
        </div>

        <div className="grid items-start gap-[18px] md:grid-cols-[1.35fr_1fr]">
          <div
            className="rounded-2xl border border-[rgba(78,201,122,.35)] bg-[#1d2026] px-6 py-[26px] sm:px-7"
            style={{ boxShadow: "0 20px 60px rgba(0,0,0,.4)" }}
          >
            <div className="mb-4 flex flex-wrap items-center gap-2.5">
              <span className="font-mono rounded border border-[rgba(78,201,122,.4)] px-2.5 py-[3px] text-[11px] font-bold text-[#4ec97a]">
                RANK #1 · 4.35/5
              </span>
              <span className="font-mono text-[10px] text-[#6d7280]">
                judge-scored · 5 criteria
              </span>
            </div>
            <h3 className="mb-4 text-[19px] leading-[1.3] font-bold text-[#f3f1ec] sm:text-[21px]">
              Does sleep restriction impair overnight memory consolidation
              more in evening-chronotype adolescents?
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-x-6">
              {SAMPLE_FIELDS.map((f) => (
                <div key={f.label}>
                  <p className="font-mono mb-1 text-[9.5px] tracking-[0.12em] text-[#6d7280]">
                    {f.label}
                  </p>
                  <p className="text-[13px] leading-[1.45] text-[#c6c4bf]">
                    {f.value}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3.5">
            <div className="rounded-2xl border border-[#2a2d35] bg-[#1a1d23] px-6 py-[22px]">
              <p className="font-mono mb-4 text-[9.5px] tracking-[0.12em] text-[#6d7280]">
                RUBRIC
              </p>
              {RUBRIC.map((r) => (
                <div key={r.label} className="mb-[13px]">
                  <div className="mb-1.5 flex justify-between text-[12.5px] text-[#c6c4bf]">
                    <span>{r.label}</span>
                    <span className="font-mono text-[#8b909c]">{r.score}</span>
                  </div>
                  <div className="h-[5px] overflow-hidden rounded-[3px] bg-[#262a32]">
                    <div
                      className="h-full rounded-[3px] bg-[#4ec97a]"
                      style={{ width: r.pct }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3 rounded-xl border border-[rgba(78,201,122,.3)] bg-[#1d2026] px-5 py-4">
              <span
                className="h-2 w-2 flex-none rounded-full bg-[#4ec97a]"
                style={{ boxShadow: "0 0 8px #4ec97a" }}
              />
              <div>
                <p className="text-[12.5px] text-[#e8e6e1]">
                  One click → exported to Notion
                </p>
                <p className="font-mono mt-0.5 text-[10px] text-[#6d7280]">
                  via MCP · full plan + citations
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-[2] mx-auto mt-24 max-w-[1060px] px-6 pb-24 sm:px-10">
        <div
          className="relative overflow-hidden rounded-[20px] border border-[#2a2d35] px-6 py-[52px] text-center sm:px-10 sm:py-[66px]"
          style={{ background: "linear-gradient(135deg,#1d2026,#16181d)" }}
        >
          <div
            className="pointer-events-none absolute top-[-160px] left-1/2 h-[420px] w-[640px] -translate-x-1/2"
            style={{
              background: `radial-gradient(ellipse at center, ${GLOW_TINT} 0%, transparent 70%)`,
            }}
          />
          <div className="relative">
            <h2 className="mx-auto max-w-[20ch] text-[30px] leading-[1.15] font-bold tracking-[-0.02em] text-[#f3f1ec] sm:text-[44px] sm:leading-[1.08]">
              Give it a question you&apos;ve been circling.
            </h2>
            <p className="mx-auto mt-5 max-w-[50ch] text-[15px] leading-[1.55] text-[#c6c4bf] sm:text-[17px]">
              Paste a brief. Watch five agents turn it into ranked plans in
              minutes — with every source and score in the open.
            </p>
            <Link
              href="/new"
              className="font-mono mt-[34px] inline-flex items-center gap-2.5 rounded-[9px] px-[30px] py-4 text-[15px] font-semibold text-[#16181d]"
              style={{ background: ACCENT, boxShadow: `0 10px 40px ${GLOW_TINT}` }}
            >
              Start a research run <span>→</span>
            </Link>
          </div>
        </div>

        <div className="font-mono mt-10 flex flex-wrap items-center justify-between gap-3.5 text-[11px] text-[#6d7280]">
          <span className="font-bold text-[#e8b04b]">co·researcher</span>
          <span>FastAPI · LangGraph · Next.js · Supabase</span>
          <span>ideate → literature → methodology → plan → judge</span>
        </div>
      </section>
    </div>
  );
}
