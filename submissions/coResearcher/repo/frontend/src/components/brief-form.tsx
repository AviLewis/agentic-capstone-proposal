"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { CapsOverride } from "@/lib/types";

interface BriefFormProps {
  onCreated: (runId: string) => void;
}

const fieldLabel =
  "font-mono block text-[10.5px] tracking-[0.1em] text-[#c6c4bf] mb-2";

const darkField =
  "w-full resize-none rounded-lg bg-[#1d2026] px-4 py-3.5 text-sm leading-relaxed text-[#e8e6e1] placeholder:text-[#6d7280] outline-none transition-colors focus:border-[#e8b04b]";

// Literature sources the backend can query. `id` must match backend source keys.
const SOURCE_OPTIONS = [
  { id: "openalex", label: "OpenAlex", note: "Open scholarly metadata" },
  { id: "arxiv", label: "arXiv", note: "Preprints" },
  {
    id: "semantic_scholar",
    label: "Semantic Scholar",
    note: "May rate-limit without a key",
  },
] as const;

export function BriefForm({ onCreated }: BriefFormProps) {
  const [brief, setBrief] = useState("");
  const [context, setContext] = useState("");
  const [ownData, setOwnData] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxQuestions, setMaxQuestions] = useState("6");
  const [maxPapers, setMaxPapers] = useState("8");
  const [costCeiling, setCostCeiling] = useState("5");
  const [sources, setSources] = useState<string[]>(["openalex", "arxiv"]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const briefValid = brief.trim().length >= 10;
  const sourcesValid = sources.length > 0;

  function toggleSource(id: string) {
    setSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!briefValid || !sourcesValid || submitting) return;
    setSubmitting(true);
    setError(null);

    const caps: CapsOverride | undefined = showAdvanced
      ? {
          max_questions: Number(maxQuestions) || undefined,
          max_papers_per_question: Number(maxPapers) || undefined,
          cost_ceiling_usd: Number(costCeiling) || undefined,
        }
      : undefined;

    try {
      const res = await api.createRun({
        brief: brief.trim(),
        researcher_context: context.trim(),
        own_data: ownData.trim(),
        caps,
        sources,
      });
      onCreated(res.run_id);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to start the run.",
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-[18px]">
      <div>
        <div className="mb-2 flex items-baseline justify-between">
          <label htmlFor="brief" className="font-mono text-[10.5px] tracking-[0.1em] text-[#c6c4bf]">
            RESEARCH BRIEF *
          </label>
          <span className="font-mono text-[10px] text-[#6d7280]">
            min 10 chars
          </span>
        </div>
        <textarea
          id="brief"
          placeholder="e.g. I want to study the effect of sleep on memory consolidation in adolescents…"
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          rows={4}
          required
          className={`${darkField} min-h-[88px] border border-[#3a3f4a]`}
        />
      </div>

      <div>
        <label htmlFor="context" className={fieldLabel}>
          RESEARCHER CONTEXT
        </label>
        <textarea
          id="context"
          placeholder="Your field, expertise, goals, and constraints…"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          rows={3}
          className={`${darkField} min-h-[56px] border border-[#2a2d35]`}
        />
      </div>

      <div>
        <label htmlFor="own-data" className={fieldLabel}>
          YOUR DATA / CONSTRAINTS
        </label>
        <textarea
          id="own-data"
          placeholder="Datasets, equipment, timeline, budget…"
          value={ownData}
          onChange={(e) => setOwnData(e.target.value)}
          rows={3}
          className={`${darkField} min-h-[56px] border border-[#2a2d35]`}
        />
      </div>

      <div className="rounded-lg border border-[#2a2d35] bg-[#131519] px-[18px] py-4">
        <span className="font-mono mb-3 block text-[10.5px] tracking-[0.1em] text-[#8b909c]">
          LITERATURE SOURCES
        </span>
        <div className="flex flex-col gap-2.5">
          {SOURCE_OPTIONS.map((src) => {
            const checked = sources.includes(src.id);
            return (
              <label
                key={src.id}
                className="flex cursor-pointer items-center gap-3 text-sm text-[#e8e6e1]"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleSource(src.id)}
                  className="h-4 w-4 accent-[#e8b04b]"
                />
                <span className="font-medium">{src.label}</span>
                <span className="font-mono text-[10.5px] text-[#6d7280]">
                  {src.note}
                </span>
              </label>
            );
          })}
        </div>
        {!sourcesValid && (
          <p className="mt-2.5 text-[11.5px] text-[#e2716b]">
            Select at least one source.
          </p>
        )}
      </div>

      <div className="rounded-lg border border-[#2a2d35] bg-[#131519] px-[18px] py-4">
        <div className="mb-3.5 flex items-center justify-between">
          <span className="font-mono text-[10.5px] tracking-[0.1em] text-[#8b909c]">
            RUN CAPS
          </span>
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="font-mono cursor-pointer text-[10px] text-[#e8b04b]"
          >
            {showAdvanced ? "− hide" : "+ show"}
          </button>
        </div>

        {showAdvanced && (
          <div className="grid grid-cols-3 gap-3.5">
            <div>
              <label htmlFor="max-questions" className="mb-1.5 block text-[11px] text-[#8b909c]">
                Max questions
              </label>
              <input
                id="max-questions"
                type="number"
                min={1}
                max={20}
                value={maxQuestions}
                onChange={(e) => setMaxQuestions(e.target.value)}
                className="font-mono w-full rounded-md border border-[#2a2d35] bg-[#1d2026] px-3 py-2 text-[13px] text-[#e8e6e1] outline-none focus:border-[#e8b04b]"
              />
            </div>
            <div>
              <label htmlFor="max-papers" className="mb-1.5 block text-[11px] text-[#8b909c]">
                Papers / question
              </label>
              <input
                id="max-papers"
                type="number"
                min={1}
                max={50}
                value={maxPapers}
                onChange={(e) => setMaxPapers(e.target.value)}
                className="font-mono w-full rounded-md border border-[#2a2d35] bg-[#1d2026] px-3 py-2 text-[13px] text-[#e8e6e1] outline-none focus:border-[#e8b04b]"
              />
            </div>
            <div>
              <label htmlFor="cost-ceiling" className="mb-1.5 block text-[11px] text-[#8b909c]">
                Cost ceiling ($)
              </label>
              <input
                id="cost-ceiling"
                type="number"
                min={0.5}
                step={0.5}
                value={costCeiling}
                onChange={(e) => setCostCeiling(e.target.value)}
                className="font-mono w-full rounded-md border border-[#2a2d35] bg-[#1d2026] px-3 py-2 text-[13px] text-[#e8e6e1] outline-none focus:border-[#e8b04b]"
              />
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-[#e2716b]">{error}</p>}

      <div className="mt-0.5 flex items-center gap-4">
        <button
          type="submit"
          disabled={!briefValid || !sourcesValid || submitting}
          className="cursor-pointer rounded-md bg-[#e8b04b] px-[26px] py-3 text-sm font-bold text-[#16181d] transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Starting…" : "Start research run"}
        </button>
        <span className="font-mono text-[11px] text-[#6d7280]">
          POST /runs
        </span>
      </div>
    </form>
  );
}
