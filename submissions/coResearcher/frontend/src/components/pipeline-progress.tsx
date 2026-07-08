"use client";

import { useEffect, useState, type CSSProperties } from "react";
import type { NodeData } from "@/lib/types";

interface Step {
  key: string;
  label: string;
  color: string;
  substeps: string[];
  description: string;
}

// The automated stretch the researcher waits through (gates are handled
// separately by the run view). Order matches the graph's node sequence.
const STEPS: Step[] = [
  {
    key: "ideating",
    label: "Ideate",
    color: "#e8b04b",
    description:
      "Generating candidate research questions from your brief, then deduping to a focused shortlist.",
    substeps: [
      "Reading your brief…",
      "Generating candidate questions…",
      "Deduping overlapping ideas…",
      "Ranking by promise…",
    ],
  },
  {
    key: "reviewing_literature",
    label: "Literature",
    color: "#4ec97a",
    description:
      "Searching OpenAlex, arXiv, and Semantic Scholar per question, then summarizing and citing the evidence.",
    substeps: [
      "Querying OpenAlex…",
      "Searching arXiv…",
      "Scanning Semantic Scholar…",
      "Summarizing key papers…",
      "Extracting relevant findings…",
    ],
  },
  {
    key: "designing_methodology",
    label: "Methodology",
    color: "#56bcd8",
    description:
      "Designing testable methods — sampling, measures, and analysis — grounded in the reviewed literature.",
    substeps: [
      "Mapping methods to questions…",
      "Selecting measures & sampling…",
      "Grounding in the literature…",
      "Identifying open gaps…",
    ],
  },
  {
    key: "planning",
    label: "Plan",
    color: "#a98ee8",
    description:
      "Drafting full research plans — objective, hypotheses, methods, data sources, and risks.",
    substeps: [
      "Drafting objectives…",
      "Outlining hypotheses…",
      "Linking data to source papers…",
      "Listing risks & resources…",
    ],
  },
  {
    key: "judging",
    label: "Judge",
    color: "#e88fb0",
    description:
      "Scoring every plan on 5 weighted criteria and ranking them by feasibility for your approval.",
    substeps: [
      "Scoring feasibility…",
      "Weighing 5 criteria…",
      "Ranking plans…",
      "Finalizing recommendations…",
    ],
  },
];

// Statuses that mean "the automated work is effectively finished".
const DONE_STATUSES = new Set([
  "awaiting_plan_approval",
  "completed",
  "capped",
]);

const DONE = STEPS.length;

// The status the backend reports names the node that just *finished*, so it lags
// one step behind the work actually running. The last completed node is the
// reliable signal: it tells us which automated step is now in progress. Note
// that after a gate resume the previously completed node (e.g. `ideator`) is
// still the most recent one, so those must map forward to the next real step —
// otherwise the bar would show ideation "working" again after the questions.
const NODE_TO_RUNNING_STEP: Record<string, string> = {
  ideator: "reviewing_literature",
  gate_questions: "reviewing_literature",
  literature_review: "designing_methodology",
  methodology: "planning",
  research_plan: "judging",
  judge: "__done__",
};

function stepIndexFromStatus(status: string): number {
  const idx = STEPS.findIndex((s) => s.key === status);
  if (idx !== -1) return idx;
  if (DONE_STATUSES.has(status)) return DONE;
  // question selection sits right after ideate; treat ideate as complete.
  if (status === "awaiting_question_selection") return 1;
  return 0;
}

function currentStepIndex(status: string, nodes: NodeData[]): number {
  const lastNode = nodes.length ? nodes[nodes.length - 1].node : null;
  if (lastNode && lastNode in NODE_TO_RUNNING_STEP) {
    const key = NODE_TO_RUNNING_STEP[lastNode];
    if (key === "__done__") return DONE;
    const idx = STEPS.findIndex((s) => s.key === key);
    if (idx !== -1) return idx;
  }
  // Otherwise fall back to the reported status (covers the first ideate run and
  // the moment right after a gate resume, before any node has completed).
  return stepIndexFromStatus(status);
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

function useElapsedSeconds(): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const start = Date.now();
    const t = setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );
    return () => clearInterval(t);
  }, []);
  return elapsed;
}

function formatElapsed(total: number): string {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function PipelineProgress({
  status,
  nodes,
}: {
  status: string;
  nodes: NodeData[];
}) {
  const reduced = usePrefersReducedMotion();
  const elapsed = useElapsedSeconds();
  const currentIndex = currentStepIndex(status, nodes);
  const boundedIndex = Math.min(currentIndex, STEPS.length - 1);
  const finished = currentIndex >= STEPS.length;

  // A user can click a stage to read what it does; otherwise we follow along.
  const [selected, setSelected] = useState<number | null>(null);
  const focusIndex = selected ?? boundedIndex;
  const focusStep = STEPS[focusIndex];

  // Rotate the current stage's substeps to keep the panel feeling alive. A
  // single monotonic tick avoids resetting state when the stage changes; the
  // displayed index is derived via modulo of the active stage's substep count.
  const activeStep = STEPS[boundedIndex];
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (reduced || finished) return;
    const t = setInterval(() => setTick((n) => n + 1), 2400);
    return () => clearInterval(t);
  }, [reduced, finished]);
  const subIdx = tick % activeStep.substeps.length;

  const pct = Math.round((currentIndex / STEPS.length) * 100);

  const activityLine =
    selected !== null
      ? focusStep.description
      : finished
        ? "Plans ready — bringing up your ranked results…"
        : activeStep.substeps[subIdx];

  return (
    <div className="rounded-xl border border-[#2a2d35] bg-[#1a1d23] p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="font-mono text-[10.5px] tracking-[0.14em] text-[#6d7280]">
          PIPELINE PROGRESS ·{" "}
          <span className="text-[#8b909c]">
            {finished ? "5 / 5" : `${boundedIndex + 1} / ${STEPS.length}`}
          </span>
        </p>
        <p className="font-mono text-[10.5px] text-[#6d7280]">
          <span className="text-[#8b909c]">{pct}%</span> · elapsed{" "}
          <span className="text-[#8b909c]">{formatElapsed(elapsed)}</span>
        </p>
      </div>

      <div className="flex gap-1.5">
        {STEPS.map((step, i) => {
          const done = i < currentIndex;
          const isCurrent = i === currentIndex && !finished;
          const state = done ? "done" : isCurrent ? "current" : "upcoming";
          return (
            <button
              key={step.key}
              type="button"
              onClick={() =>
                setSelected((prev) => (prev === i ? null : i))
              }
              className="seg-btn"
              aria-label={step.label}
              data-selected={selected === i || undefined}
            >
              <span
                className={`seg seg-${state}`}
                style={{ "--c": step.color } as CSSProperties}
              />
            </button>
          );
        })}
      </div>

      <div className="mt-2.5 flex justify-between">
        {STEPS.map((step, i) => {
          const done = i < currentIndex;
          const isCurrent = i === currentIndex && !finished;
          const color = done
            ? "#4ec97a"
            : isCurrent
              ? step.color
              : selected === i
                ? "#c6c4bf"
                : "#6d7280";
          return (
            <span
              key={step.key}
              className="font-mono text-[10px]"
              style={{ color, flex: 1, textAlign: "center" }}
            >
              {step.label}
            </span>
          );
        })}
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-[#23262e] pt-3.5">
        <span
          className="dot"
          style={{
            background: finished ? "#4ec97a" : activeStep.color,
            boxShadow: `0 0 8px ${finished ? "#4ec97a" : activeStep.color}`,
          }}
        />
        <p className="text-[12.5px] text-[#c6c4bf]" aria-live="polite">
          {activityLine}
          {!reduced && selected === null && !finished && (
            <span className="cursor-blink">▊</span>
          )}
        </p>
      </div>

      <style jsx>{`
        .seg-btn {
          flex: 1;
          padding: 4px 0;
          background: transparent;
          border: none;
          cursor: pointer;
        }
        .seg {
          display: block;
          height: 6px;
          border-radius: 4px;
          background: #2a2d35;
          position: relative;
          overflow: hidden;
          transition: background 0.4s;
        }
        .seg-done {
          background: #4ec97a;
        }
        .seg-current {
          background: color-mix(in srgb, var(--c) 45%, #2a2d35);
        }
        .seg-current::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(
            90deg,
            transparent,
            var(--c),
            transparent
          );
          transform: translateX(-100%);
          animation: sweep 1.5s ease-in-out infinite;
        }
        .seg-btn[data-selected] .seg {
          outline: 1px solid #4a4f5a;
          outline-offset: 2px;
        }
        .dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          flex: none;
          animation: pulse 1.4s ease-in-out infinite;
        }
        .cursor-blink {
          margin-left: 2px;
          animation: blink 1s step-end infinite;
          color: #6d7280;
        }
        @keyframes sweep {
          to {
            transform: translateX(100%);
          }
        }
        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0.35;
          }
        }
        @keyframes blink {
          50% {
            opacity: 0;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .seg-current::after,
          .dot,
          .cursor-blink {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}
