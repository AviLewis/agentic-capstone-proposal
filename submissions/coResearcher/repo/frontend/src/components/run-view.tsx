"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { NodeData, RunResults, RunStatus } from "@/lib/types";
import { useRunStream } from "@/lib/use-run-stream";
import { ConsoleTopBar } from "@/components/console-topbar";
import { PipelineSidebar } from "@/components/pipeline-sidebar";
import { PipelineProgress } from "@/components/pipeline-progress";
import { QuestionGate } from "@/components/question-gate";
import { PlanApprovalGate } from "@/components/plan-approval-gate";
import {
  EmptyState,
  ResultsView,
  ResultTabPanel,
  ResultTabsBar,
  resultTabDescriptors,
  type ResultTabId,
  type TabDescriptor,
} from "@/components/results-view";

type LiveTabId = "pipeline" | ResultTabId;

// Tab descriptors shown before any results have been fetched, so the tab strip
// is present (with zero counts) from the very first render.
const EMPTY_RESULT_TABS: TabDescriptor<ResultTabId>[] = [
  { id: "plans", label: "Ranked plans", count: 0 },
  { id: "literature", label: "Literature", count: 0 },
  { id: "methodology", label: "Methodology", count: 0 },
  { id: "questions", label: "Questions", count: 0 },
];

const STATUS_TITLES: Record<string, string> = {
  connecting: "Connecting…",
  running: "Working…",
  pending: "Starting run…",
  ideating: "Generating research questions",
  reviewing_literature: "Reviewing literature",
  designing_methodology: "Designing methodology",
  planning: "Drafting research plans",
  judging: "Scoring & ranking plans",
};

// Runs in one of these states have finished: their results are fully persisted
// and can be rendered straight from GET /runs/{id} without waiting on the SSE
// snapshot (which reads the LangGraph checkpoint from the remote DB).
const TERMINAL_STATUSES = new Set<RunStatus>(["completed", "capped", "error"]);

const NODE_LABELS: Record<string, string> = {
  ideator: "Ideator",
  gate_questions: "Question selection",
  literature_review: "Literature review",
  methodology: "Methodology",
  research_plan: "Research plan",
  judge: "Judge",
  gate_plan_approval: "Plan approval",
};

function SourceHealthBanner({ nodes }: { nodes: NodeData[] }) {
  // Merge source_health across every streamed node (source -> latest reason).
  const failed: Record<string, string> = {};
  for (const n of nodes) {
    if (n.source_health) {
      for (const [src, reason] of Object.entries(n.source_health)) {
        failed[src] = reason;
      }
    }
  }
  const entries = Object.entries(failed);
  if (entries.length === 0) return null;

  return (
    <div className="mb-6 max-w-[660px] rounded-lg border border-[rgba(232,176,75,.4)] bg-[rgba(232,176,75,.08)] px-4 py-3">
      <p className="font-mono mb-1 text-[10.5px] tracking-[0.14em] text-[#e8b04b]">
        SOURCE ISSUES
      </p>
      {entries.map(([src, reason]) => (
        <p key={src} className="text-[12.5px] text-[#e8e6e1]">
          <span className="font-semibold">{src}</span>: {reason} — results may
          be incomplete. You can disable it when starting a new run.
        </p>
      ))}
    </div>
  );
}

function RunningPanel({ status, nodes }: { status: string; nodes: NodeData[] }) {
  const connecting = status === "connecting";
  return (
    <div>
      <p className="font-mono mb-1.5 text-[10.5px] tracking-[0.14em] text-[#4ec97a]">
        {connecting ? "CONNECTING…" : "LIVE · SSE CONNECTED"}
      </p>
      <h1 className="mb-6 text-2xl font-bold text-white">
        {STATUS_TITLES[status] ?? status}
      </h1>

      <SourceHealthBanner nodes={nodes} />

      {!connecting && (
        <div className="mb-6 max-w-[660px]">
          <PipelineProgress status={status} nodes={nodes} />
        </div>
      )}

      <div className="flex max-w-[660px] flex-col gap-4">
        {nodes.length === 0 && (
          <p className="text-sm text-[#8b909c]">
            {connecting
              ? "Loading run — restoring live progress…"
              : "Waiting for the pipeline to start…"}
          </p>
        )}
        {nodes.map((n, i) => (
          <div
            key={`${n.node}-${i}`}
            className="rounded-lg border border-[#2a2d35] bg-[#1d2026] px-5 py-4"
          >
            <p className="mb-1.5 text-sm font-semibold text-white">
              {NODE_LABELS[n.node] ?? n.node}
            </p>
            {n.logs?.map((log, j) => (
              <p key={j} className="text-[12.5px] text-[#8b909c]">
                {log}
              </p>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function RunView({ runId }: { runId: string }) {
  const stream = useRunStream(runId);
  const [results, setResults] = useState<RunResults | null>(null);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [costCeilingUsd, setCostCeilingUsd] = useState<number | null>(null);
  const [liveResults, setLiveResults] = useState<RunResults | null>(null);
  const [liveTab, setLiveTab] = useState<LiveTabId>("pipeline");

  // Fetch the persisted run on mount. This powers the cost-ceiling bar and, for
  // runs that already finished, lets us render results immediately instead of
  // waiting for the slower SSE snapshot round-trip through the remote DB.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getRun(runId);
        if (cancelled) return;
        setCostCeilingUsd(res.run.caps?.cost_ceiling_usd ?? null);
        if (TERMINAL_STATUSES.has(res.run.status)) setResults(res);
      } catch {
        // best-effort; the cost ceiling bar just won't show a fraction.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    if (!stream.completed) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getRun(runId);
        if (!cancelled) setResults(res);
      } catch (err) {
        if (!cancelled) {
          setResultsError(
            err instanceof ApiError ? err.message : "Failed to load results.",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [stream.completed, runId]);

  // Render results as soon as we have them, whether they arrived via the mount
  // fetch (already-finished run) or the SSE `completed` event (live run).
  const showResults = stream.completed || results !== null;

  // While the run is still in progress, poll the persisted (partial) results so
  // the user can browse questions/literature/methodology/plans as each step
  // completes — not just at the end. Node completions also trigger an immediate
  // refetch so tabs feel responsive.
  useEffect(() => {
    if (showResults) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await api.getRun(runId);
        if (!cancelled) setLiveResults(res);
      } catch {
        // best-effort; the tabs just stay on their last known contents.
      }
    };
    poll();
    const timer = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [runId, showResults, stream.nodes.length]);

  // A HITL gate needs the user's attention, so surface the Pipeline tab when one
  // appears (in case they were browsing another tab). Adjusting state during
  // render, guarded by the previous value, avoids an extra effect-driven pass.
  const gateKey = stream.gate?.gate ?? null;
  const [prevGateKey, setPrevGateKey] = useState(gateKey);
  if (gateKey !== prevGateKey) {
    setPrevGateKey(gateKey);
    if (gateKey) setLiveTab("pipeline");
  }

  if (showResults) {
    return (
      <div className="flex min-h-screen flex-col bg-[#16181d] text-[#e8e6e1]">
        <ConsoleTopBar
          runId={runId}
          cost={stream.cost}
          status={results?.run.status ?? stream.status}
        />
        <main className="flex-1 px-11 py-8">
          {results ? (
            <ResultsView
              runId={runId}
              results={results}
              approvedPlanId={stream.approvedPlanId}
            />
          ) : resultsError ? (
            <p className="text-sm text-[#e2716b]">{resultsError}</p>
          ) : (
            <p className="text-sm text-[#8b909c]">Loading results…</p>
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#16181d] text-[#e8e6e1]">
      <ConsoleTopBar runId={runId} cost={stream.cost} status={stream.status} />
      <div className="flex flex-1">
        <PipelineSidebar
          status={stream.status}
          costUsd={stream.cost?.cost_usd ?? 0}
          costCeilingUsd={costCeilingUsd}
        />
        <main className="flex-1 overflow-auto px-9 py-[30px]">
          {stream.error ? (
            <p className="text-sm text-[#e2716b]">{stream.error}</p>
          ) : (
            <>
              <ResultTabsBar
                label="Run stages (live)"
                active={liveTab}
                onSelect={setLiveTab}
                tabs={[
                  {
                    id: "pipeline",
                    label: "Pipeline",
                    badge: stream.gate ? (
                      <span className="font-mono rounded bg-[#e8b04b] px-1.5 py-0.5 text-[9px] font-bold text-[#16181d]">
                        NEEDS INPUT
                      </span>
                    ) : (
                      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[#4ec97a]" />
                    ),
                  },
                  ...(liveResults
                    ? resultTabDescriptors(liveResults)
                    : EMPTY_RESULT_TABS),
                ]}
              />

              {liveTab === "pipeline" ? (
                stream.gate?.gate === "question_selection" ? (
                  <QuestionGate
                    questions={stream.gate.questions}
                    onSubmit={(ids) =>
                      stream.resume("question_selection", { selected_ids: ids })
                    }
                  />
                ) : stream.gate?.gate === "plan_approval" ? (
                  <PlanApprovalGate
                    rankedPlans={stream.gate.ranked_plans}
                    onApprove={(planId) =>
                      stream.resume("plan_approval", {
                        approved_plan_id: planId,
                      })
                    }
                  />
                ) : (
                  <RunningPanel status={stream.status} nodes={stream.nodes} />
                )
              ) : liveResults ? (
                <ResultTabPanel
                  tab={liveTab}
                  results={liveResults}
                  approvedPlanId={stream.approvedPlanId}
                />
              ) : (
                <EmptyState label="Loading results so far…" />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
