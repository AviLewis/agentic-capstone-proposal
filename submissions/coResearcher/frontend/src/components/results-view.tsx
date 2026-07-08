"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type {
  Paper,
  Methodology,
  Question,
  RankedPlan,
  RunResults,
} from "@/lib/types";
import { PlanContentView } from "@/components/plan-content";

function formatCriterion(name: string) {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function questionLabel(q: Question, index: number) {
  return `Q${index + 1} · ${q.tag ?? q.text.slice(0, 44) + (q.text.length > 44 ? "…" : "")}`;
}

export type ResultTabId = "plans" | "literature" | "methodology" | "questions";

const sectionLabel =
  "font-mono mb-2.5 text-[9.5px] tracking-[0.12em] text-[#6d7280]";

// --- shared derived data ----------------------------------------------------

function useRankedPlans(results: RunResults) {
  return useMemo(
    () =>
      [...results.ranked_plans].sort(
        (a, b) => (a.plan.rank ?? 999) - (b.plan.rank ?? 999),
      ),
    [results.ranked_plans],
  );
}

function usePapersByQuestion(results: RunResults) {
  return useMemo(() => {
    const map = new Map<string, Paper[]>();
    for (const p of results.papers) {
      const list = map.get(p.question_id) ?? [];
      list.push(p);
      map.set(p.question_id, list);
    }
    return map;
  }, [results.papers]);
}

function useMethodologyByQuestion(results: RunResults) {
  return useMemo(() => {
    const map = new Map<string, Methodology>();
    for (const m of results.methodologies) map.set(m.question_id, m);
    return map;
  }, [results.methodologies]);
}

function useSelectedQuestions(results: RunResults) {
  return useMemo(
    () =>
      [...results.questions]
        .filter((q) => q.selected)
        .sort((a, b) => a.position - b.position),
    [results.questions],
  );
}

function useAllQuestions(results: RunResults) {
  return useMemo(
    () => [...results.questions].sort((a, b) => a.position - b.position),
    [results.questions],
  );
}

// Literature/methodology are keyed off selected questions once Gate 1 has been
// passed; before that we fall back to all generated questions so the tabs still
// have context to show mid-run.
function useEvidenceQuestions(results: RunResults) {
  const selected = useSelectedQuestions(results);
  const all = useAllQuestions(results);
  return selected.length > 0 ? selected : all;
}

// --- shared tab bar ---------------------------------------------------------

export interface TabDescriptor<T extends string> {
  id: T;
  label: string;
  count?: number;
  badge?: ReactNode;
}

export function ResultTabsBar<T extends string>({
  tabs,
  active,
  onSelect,
  label = "Run stages",
}: {
  tabs: TabDescriptor<T>[];
  active: T;
  onSelect: (id: T) => void;
  label?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="font-mono mb-6 flex flex-wrap gap-1 border-b border-[#2a2d35]"
    >
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          type="button"
          aria-selected={active === t.id}
          onClick={() => onSelect(t.id)}
          className="-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-[13px] font-medium transition-colors"
          style={{
            borderColor: active === t.id ? "#e8b04b" : "transparent",
            color: active === t.id ? "#fff" : "#8b909c",
          }}
        >
          {t.label}
          {t.count != null && (
            <span className="text-[11px] text-[#6d7280]">{t.count}</span>
          )}
          {t.badge}
        </button>
      ))}
    </div>
  );
}

export function resultTabDescriptors(
  results: RunResults,
): TabDescriptor<ResultTabId>[] {
  return [
    { id: "plans", label: "Ranked plans", count: results.ranked_plans.length },
    { id: "literature", label: "Literature", count: results.papers.length },
    {
      id: "methodology",
      label: "Methodology",
      count: results.methodologies.length,
    },
    { id: "questions", label: "Questions", count: results.questions.length },
  ];
}

// --- tab panels (reused by ResultsView and the live run browser) ------------

export function PlansPanel({
  results,
  approvedPlanId,
}: {
  results: RunResults;
  approvedPlanId: string | null;
}) {
  const rankedPlans = useRankedPlans(results);
  const papersByQuestion = usePapersByQuestion(results);
  const evidenceQuestions = useEvidenceQuestions(results);

  const papersBySource = useMemo(() => {
    const map = new Map<string, number>();
    for (const p of results.papers) {
      map.set(p.source, (map.get(p.source) ?? 0) + 1);
    }
    return [...map.entries()];
  }, [results.papers]);

  const approvedPlan =
    rankedPlans.find((rp) => rp.plan.id === approvedPlanId) ?? rankedPlans[0];
  const runnerUps = rankedPlans.filter(
    (rp) => rp.plan.id !== approvedPlan?.plan.id,
  );

  return (
    <section className="flex max-w-[920px] flex-col gap-5">
      {rankedPlans.length === 0 ? (
        <EmptyState label="No plans yet — they appear after the planning and judging steps." />
      ) : (
        <div className="flex gap-5">
          {approvedPlan && (
            <div className="flex-[1.4] rounded-lg border border-[rgba(78,201,122,.35)] bg-[#1d2026] px-6 py-5.5">
              <div className="mb-3 flex items-center gap-2.5">
                <span className="font-mono rounded bg-[#4ec97a] px-2 py-0.5 text-[10px] font-bold text-[#16181d]">
                  {approvedPlanId === approvedPlan.plan.id
                    ? "APPROVED"
                    : "TOP RANKED"}
                </span>
                <span className="font-mono text-[11px] text-[#8b909c]">
                  rank #{approvedPlan.plan.rank ?? "—"}
                  {approvedPlan.plan.feasibility_total != null &&
                    ` · ${approvedPlan.plan.feasibility_total.toFixed(2)}/5`}
                </span>
              </div>
              <PlanContentView content={approvedPlan.plan.content_json} />
            </div>
          )}

          <div className="flex flex-1 flex-col gap-4">
            <div className="rounded-lg border border-[#2a2d35] bg-[#1d2026] px-5 py-4.5">
              <p className={sectionLabel}>EVIDENCE BASE</p>
              <div className="flex flex-col gap-3">
                {evidenceQuestions.map((q, i) => (
                  <div key={q.id}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[13px] leading-snug text-[#e8e6e1]">
                        {questionLabel(q, i)}
                      </span>
                      <span className="font-mono flex-none text-[11px] text-[#8b909c]">
                        {(papersByQuestion.get(q.id) ?? []).length} papers
                      </span>
                    </div>
                    {i < evidenceQuestions.length - 1 && (
                      <div className="mt-3 h-px bg-[#2a2d35]" />
                    )}
                  </div>
                ))}
              </div>
              {papersBySource.length > 0 && (
                <div className="font-mono mt-3.5 flex gap-4 border-t border-[#2a2d35] pt-3.5 text-[10px] text-[#6d7280]">
                  {papersBySource.map(([source, count]) => (
                    <span key={source}>
                      {source} <span className="text-[#c6c4bf]">{count}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {runnerUps.map((rp) => (
              <div
                key={rp.plan.id}
                className="rounded-lg border border-[#2a2d35] px-5 py-4 opacity-85"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-mono text-[10px] font-bold text-[#8b909c]">
                    RANK #{rp.plan.rank ?? "—"}
                    {rp.plan.feasibility_total != null &&
                      ` · ${rp.plan.feasibility_total.toFixed(2)}/5`}
                  </span>
                </div>
                <p className="text-[13px] leading-snug text-[#c6c4bf]">
                  {rp.plan.content_json.objective ?? "—"}
                </p>
              </div>
            ))}

            {approvedPlan?.plan.notion_url && (
              <div className="flex items-center gap-3 rounded-lg border border-[rgba(78,201,122,.3)] bg-[#1d2026] px-5 py-4">
                <div className="h-2 w-2 flex-none rounded-full bg-[#4ec97a]" />
                <div>
                  <p className="text-[12.5px] text-[#e8e6e1]">
                    Exported to Notion
                  </p>
                  <a
                    href={approvedPlan.plan.notion_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-[10px] text-[#6d7280] hover:text-[#8b909c]"
                  >
                    view in Notion ↗
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {rankedPlans.map((rp) => (
        <ScoreBreakdown key={rp.plan.id} rankedPlan={rp} />
      ))}
    </section>
  );
}

export function LiteraturePanel({ results }: { results: RunResults }) {
  const papersByQuestion = usePapersByQuestion(results);
  const evidenceQuestions = useEvidenceQuestions(results);

  return (
    <section className="flex max-w-[920px] flex-col gap-4">
      {evidenceQuestions.length === 0 ? (
        <EmptyState label="No literature yet — it appears during the literature review step." />
      ) : (
        evidenceQuestions.map((q) => (
          <LiteratureCard
            key={q.id}
            question={q}
            papers={papersByQuestion.get(q.id) ?? []}
          />
        ))
      )}
    </section>
  );
}

export function MethodologyPanel({ results }: { results: RunResults }) {
  const methodologyByQuestion = useMethodologyByQuestion(results);
  const evidenceQuestions = useEvidenceQuestions(results);

  return (
    <section className="flex max-w-[920px] flex-col gap-4">
      {evidenceQuestions.length === 0 ? (
        <EmptyState label="No methodology yet — it appears during the methodology step." />
      ) : (
        evidenceQuestions.map((q) => {
          const method = methodologyByQuestion.get(q.id);
          return (
            <div
              key={q.id}
              className="rounded-lg border border-[#2a2d35] bg-[#1d2026] px-5 py-4.5"
            >
              <p className="mb-3 text-[14px] font-semibold text-white">
                {q.text}
              </p>
              {method ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <MethodList label="Methods" items={method.methods} />
                  <MethodList label="Datasets" items={method.datasets} />
                  <MethodList label="Gaps" items={method.gaps} />
                </div>
              ) : (
                <p className="text-[12.5px] text-[#8b909c]">
                  Not designed yet.
                </p>
              )}
            </div>
          );
        })
      )}
    </section>
  );
}

export function QuestionsPanel({ results }: { results: RunResults }) {
  const allQuestions = useAllQuestions(results);

  return (
    <section className="flex max-w-[920px] flex-col gap-4">
      {allQuestions.length === 0 ? (
        <EmptyState label="No questions yet — the ideator is still generating them." />
      ) : (
        allQuestions.map((q) => (
          <div
            key={q.id}
            className="rounded-lg px-5 py-4"
            style={{
              border: `1px solid ${q.selected ? "#e8b04b" : "#2a2d35"}`,
              background: "#1d2026",
            }}
          >
            <div className="mb-1 flex items-center gap-2">
              <p className="text-[14px] font-semibold text-white">{q.text}</p>
              {q.selected && (
                <span className="font-mono rounded bg-[rgba(78,201,122,.12)] px-1.5 py-0.5 text-[10px] text-[#4ec97a]">
                  SELECTED
                </span>
              )}
              {q.tag && (
                <span className="font-mono rounded bg-[rgba(232,176,75,.12)] px-1.5 py-0.5 text-[10px] text-[#e8b04b]">
                  {q.tag}
                </span>
              )}
            </div>
            {q.rationale && (
              <p className="text-[12.5px] text-[#8b909c]">{q.rationale}</p>
            )}
          </div>
        ))
      )}
    </section>
  );
}

export function ResultTabPanel({
  tab,
  results,
  approvedPlanId,
}: {
  tab: ResultTabId;
  results: RunResults;
  approvedPlanId: string | null;
}) {
  switch (tab) {
    case "plans":
      return <PlansPanel results={results} approvedPlanId={approvedPlanId} />;
    case "literature":
      return <LiteraturePanel results={results} />;
    case "methodology":
      return <MethodologyPanel results={results} />;
    case "questions":
      return <QuestionsPanel results={results} />;
  }
}

// --- completed-run view -----------------------------------------------------

interface ResultsViewProps {
  runId: string;
  results: RunResults;
  approvedPlanId: string | null;
}

export function ResultsView({
  runId,
  results,
  approvedPlanId,
}: ResultsViewProps) {
  const [tab, setTab] = useState<ResultTabId>("plans");

  const rankedPlans = useRankedPlans(results);
  const selectedQuestions = useSelectedQuestions(results);
  const approvedPlan =
    rankedPlans.find((rp) => rp.plan.id === approvedPlanId) ?? rankedPlans[0];

  return (
    <div>
      <div className="mb-7 flex max-w-[920px] items-start justify-between gap-6">
        <div>
          <p className="font-mono mb-1.5 text-[10.5px] tracking-[0.14em] text-[#4ec97a]">
            RUN COMPLETE · {selectedQuestions.length} QUESTIONS ·{" "}
            {results.papers.length} PAPERS · {rankedPlans.length} PLANS
          </p>
          <h1 className="max-w-[600px] text-2xl font-bold leading-snug text-white">
            {results.project.brief}
          </h1>
        </div>
        <div className="flex flex-none gap-2.5">
          {approvedPlan && (
            <ExportButton runId={runId} rankedPlan={approvedPlan} />
          )}
          <Link
            href="/new"
            className="rounded-md border border-[#2a2d35] px-5 py-2.5 text-[13.5px] font-semibold text-[#c6c4bf]"
          >
            New run
          </Link>
        </div>
      </div>

      <ResultTabsBar
        tabs={resultTabDescriptors(results)}
        active={tab}
        onSelect={setTab}
      />

      <ResultTabPanel tab={tab} results={results} approvedPlanId={approvedPlanId} />
    </div>
  );
}

export function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-[#2a2d35] bg-[#1d2026] px-5 py-5 text-[13px] text-[#8b909c]">
      {label}
    </div>
  );
}

function LiteratureCard({
  question,
  papers,
}: {
  question: Question;
  papers: Paper[];
}) {
  return (
    <div className="rounded-lg border border-[#2a2d35] bg-[#1d2026] px-5 py-4.5">
      <div className="mb-3 flex items-center gap-2">
        <p className="text-[14px] font-semibold text-white">{question.text}</p>
        <span className="font-mono text-[11px] text-[#8b909c]">
          {papers.length} paper(s)
        </span>
      </div>
      {papers.length === 0 ? (
        <p className="text-[12.5px] text-[#8b909c]">No relevant papers found.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {papers.map((p) => (
            <li key={p.id} className="text-[13px] leading-relaxed">
              {p.url ? (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-[#e8e6e1] hover:underline"
                >
                  {p.title}
                </a>
              ) : (
                <span className="font-medium text-[#e8e6e1]">{p.title}</span>
              )}
              <span className="text-[#6d7280]">
                {" "}
                — {p.source}
                {p.year ? `, ${p.year}` : ""}
              </span>
              {p.relevance && (
                <p className="mt-0.5 text-[11.5px] text-[#6d7280]">
                  {p.relevance}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MethodList({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="font-mono mb-1.5 text-[9.5px] tracking-[0.12em] text-[#6d7280]">
        {label.toUpperCase()}
      </p>
      <ul className="list-disc space-y-1 pl-4 text-[12.5px] text-[#c6c4bf]">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function ScoreBreakdown({ rankedPlan }: { rankedPlan: RankedPlan }) {
  const { scores } = rankedPlan;
  if (scores.length === 0) return null;
  return (
    <div className="rounded-lg border border-[#2a2d35] bg-[#1d2026] px-5 py-4.5">
      <p className={sectionLabel}>
        RANK #{rankedPlan.plan.rank ?? "—"} · SCORE BREAKDOWN
      </p>
      <div className="flex flex-col gap-1.5">
        {scores.map((s) => (
          <div key={s.id} className="text-[12.5px]">
            <div className="flex justify-between">
              <span className="text-[#c6c4bf]">
                {formatCriterion(s.criterion)}
              </span>
              <span className="font-mono text-[#8b909c]">
                {s.score}/5 (w {s.weight})
              </span>
            </div>
            {s.justification && (
              <p className="text-[11.5px] text-[#6d7280]">{s.justification}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ExportButton({
  runId,
  rankedPlan,
}: {
  runId: string;
  rankedPlan: RankedPlan;
}) {
  const [notionUrl, setNotionUrl] = useState<string | null>(
    rankedPlan.plan.notion_url ?? null,
  );
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function exportPlan() {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const res = await api.exportToNotion(runId, rankedPlan.plan.id);
      setNotionUrl(res.notion_url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Notion export failed.");
    } finally {
      setExporting(false);
    }
  }

  if (notionUrl) {
    return (
      <a
        href={notionUrl}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-2 rounded-md bg-[#e8b04b] px-5 py-2.5 text-[13.5px] font-bold text-[#16181d]"
      >
        View in Notion ↗
      </a>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={exportPlan}
        disabled={exporting}
        className="flex items-center gap-2 rounded-md bg-[#e8b04b] px-5 py-2.5 text-[13.5px] font-bold text-[#16181d] transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
      >
        {exporting ? "Exporting…" : "Export to Notion ↗"}
      </button>
      {error && <span className="text-[11px] text-[#e2716b]">{error}</span>}
    </div>
  );
}
