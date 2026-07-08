"use client";

import { useState } from "react";
import type { GateQuestion } from "@/lib/types";

interface QuestionGateProps {
  questions: GateQuestion[];
  onSubmit: (selectedIds: string[]) => Promise<void>;
}

export function QuestionGate({ questions, onSubmit }: QuestionGateProps) {
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(questions.map((q) => q.id)),
  );
  const [submitting, setSubmitting] = useState(false);

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  async function submit() {
    if (selected.size === 0 || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit([...selected]);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <p className="font-mono mb-1.5 text-[10.5px] tracking-[0.14em] text-[#e8b04b]">
        GATE 1/2 — QUESTION SELECTION
      </p>
      <h1 className="mb-2 text-2xl font-bold text-white">
        Select research questions
      </h1>
      <p className="mb-6 max-w-[540px] text-[13.5px] leading-relaxed text-[#8b909c]">
        Choose which questions should proceed to literature review and
        planning.
      </p>

      <div className="flex max-w-[660px] flex-col gap-3">
        {questions.map((q) => {
          const checked = selected.has(q.id);
          return (
            <label
              key={q.id}
              className="flex cursor-pointer gap-3 rounded-lg p-4 transition-colors"
              style={{
                background: checked ? "#1d2026" : "transparent",
                border: `1px solid ${checked ? "#e8b04b" : "#2a2d35"}`,
              }}
            >
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-[#e8b04b]"
                checked={checked}
                onChange={() => toggle(q.id)}
              />
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <p className="text-[14px] font-semibold text-white">
                    {q.text}
                  </p>
                  {q.tag && (
                    <span className="font-mono rounded-sm bg-[rgba(232,176,75,.12)] px-1.5 py-0.5 text-[10px] text-[#e8b04b]">
                      {q.tag}
                    </span>
                  )}
                </div>
                {q.rationale && (
                  <p className="text-[12.5px] leading-relaxed text-[#8b909c]">
                    {q.rationale}
                  </p>
                )}
              </div>
            </label>
          );
        })}

        <div className="mt-2 flex items-center gap-4">
          <button
            type="button"
            onClick={submit}
            disabled={selected.size === 0 || submitting}
            className="cursor-pointer rounded-md bg-[#e8b04b] px-6 py-3 text-sm font-bold text-[#16181d] transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting
              ? "Submitting…"
              : `Continue with ${selected.size} question${selected.size === 1 ? "" : "s"}`}
          </button>
          <span className="font-mono text-[11px] text-[#6d7280]">
            then → literature review
          </span>
        </div>
      </div>
    </div>
  );
}
