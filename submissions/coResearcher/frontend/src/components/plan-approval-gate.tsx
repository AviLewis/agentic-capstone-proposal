"use client";

import { useState } from "react";
import type { GateRankedPlan } from "@/lib/types";
import { PlanContentView } from "@/components/plan-content";

interface PlanApprovalGateProps {
  rankedPlans: GateRankedPlan[];
  onApprove: (planId: string) => Promise<void>;
}

function formatCriterion(name: string) {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function PlanApprovalGate({
  rankedPlans,
  onApprove,
}: PlanApprovalGateProps) {
  const sorted = [...rankedPlans].sort((a, b) => a.rank - b.rank);
  const [selectedId, setSelectedId] = useState<string>(
    () => sorted[0]?.plan.id ?? "",
  );
  const [submitting, setSubmitting] = useState(false);

  async function approve() {
    if (!selectedId || submitting) return;
    setSubmitting(true);
    try {
      await onApprove(selectedId);
    } finally {
      setSubmitting(false);
    }
  }

  const selected = sorted.find((rp) => rp.plan.id === selectedId);

  return (
    <div>
      <p className="font-mono mb-1.5 text-[10.5px] tracking-[0.14em] text-[#e8b04b]">
        GATE 2/2 — PLAN APPROVAL
      </p>
      <h1 className="mb-2 text-2xl font-bold text-white">
        Approve a research plan
      </h1>
      <p className="mb-6 max-w-[540px] text-[13.5px] leading-relaxed text-[#8b909c]">
        Ranked by weighted feasibility. The approved plan is exported to
        Notion.
      </p>

      <div className="flex max-w-[660px] flex-col gap-3.5">
        {sorted.map((rp) => {
          const checked = selectedId === rp.plan.id;
          return (
            <label
              key={rp.plan.id}
              className="block cursor-pointer rounded-lg p-5"
              style={{
                background: checked ? "#1d2026" : "transparent",
                border: `1px solid ${checked ? "#e8b04b" : "#2a2d35"}`,
                opacity: checked ? 1 : 0.75,
              }}
            >
              <div className="mb-3.5 flex items-center gap-3">
                <input
                  type="radio"
                  name="approve-plan"
                  className="sr-only"
                  checked={checked}
                  onChange={() => setSelectedId(rp.plan.id)}
                />
                <div
                  className="flex h-4 w-4 flex-none items-center justify-center rounded-full"
                  style={{
                    border: `${checked ? 2 : 1.5}px solid ${checked ? "#e8b04b" : "#4a4f5a"}`,
                  }}
                >
                  {checked && (
                    <div className="h-[7px] w-[7px] rounded-full bg-[#e8b04b]" />
                  )}
                </div>
                <span
                  className="font-mono text-[11px] font-bold"
                  style={{ color: checked ? "#e8b04b" : "#8b909c" }}
                >
                  RANK #{rp.rank}
                </span>
                <span className="flex-1" />
                <span
                  className="font-mono rounded px-2.5 py-1 text-[12px] font-bold"
                  style={
                    checked
                      ? { color: "#16181d", background: "#e8b04b" }
                      : { color: "#c6c4bf", border: "1px solid #2a2d35" }
                  }
                >
                  {rp.total.toFixed(2)} / 5
                </span>
              </div>

              {checked ? (
                <>
                  <PlanContentView content={rp.plan.content} />
                  <div className="mt-3.5 grid grid-cols-2 gap-x-6 gap-y-2">
                    {rp.scores.map((s) => (
                      <div key={s.criterion}>
                        <div className="mb-1 flex justify-between text-[11.5px]">
                          <span className="text-[#c6c4bf]">
                            {formatCriterion(s.criterion)}
                          </span>
                          <span className="font-mono text-[#8b909c]">
                            {s.score}/5
                          </span>
                        </div>
                        <div className="h-[3px] rounded-full bg-[#2a2d35]">
                          <div
                            className="h-[3px] rounded-full bg-[#e8b04b]"
                            style={{
                              width: `${Math.min(100, (s.score / 5) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                rp.plan.content.objective && (
                  <p className="text-[12.5px] leading-relaxed text-[#6d7280]">
                    {rp.plan.content.objective}
                  </p>
                )
              )}
            </label>
          );
        })}

        <div className="mt-1 flex items-center gap-4">
          <button
            type="button"
            onClick={approve}
            disabled={!selectedId || submitting}
            className="cursor-pointer rounded-md bg-[#e8b04b] px-6 py-3 text-sm font-bold text-[#16181d] transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting
              ? "Approving…"
              : `Approve plan #${selected?.rank ?? ""}`}
          </button>
          <span className="font-mono text-[11px] text-[#6d7280]">
            then → notion export
          </span>
        </div>
      </div>
    </div>
  );
}
