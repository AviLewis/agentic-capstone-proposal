"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";

export interface PipelineStage {
  id: string;
  label: string;
  tag: string;
  color: string;
  description: string;
}

export const PIPELINE_STAGES: readonly PipelineStage[] = [
  {
    id: "ideate",
    label: "Ideate",
    tag: "IDEATOR",
    color: "#e8b04b",
    description:
      "Generates candidate research questions from your brief, then dedupes them down to a focused shortlist.",
  },
  {
    id: "literature",
    label: "Literature review",
    tag: "LIT REVIEW",
    color: "#4ec97a",
    description:
      "Searches OpenAlex, arXiv, and Semantic Scholar per selected question; summarizes and cites the evidence.",
  },
  {
    id: "methodology",
    label: "Methodology",
    tag: "METHODOLOGY",
    color: "#56bcd8",
    description:
      "Designs testable methods — sampling, measures, and analysis — grounded in the reviewed literature.",
  },
  {
    id: "plan",
    label: "Research plan",
    tag: "RESEARCH PLAN",
    color: "#a98ee8",
    description:
      "Drafts full research plans with hypotheses, methods, and risks for each viable question.",
  },
  {
    id: "judge",
    label: "Judge",
    tag: "JUDGE",
    color: "#e88fb0",
    description:
      "Scores every plan on 5 criteria and ranks them by weighted feasibility for your approval.",
  },
] as const;

const CYCLE_MS = 2200;
const RESUME_MS = 9000;

function hexToRgba(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const r = parseInt(value.substring(0, 2), 16);
  const g = parseInt(value.substring(2, 4), 16);
  const b = parseInt(value.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function usePipelineTicker() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const resumeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mql.addEventListener("change", handleChange);
    return () => mql.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    if (paused || reducedMotion) return;
    const interval = setInterval(() => {
      setActiveIndex((i) => (i + 1) % PIPELINE_STAGES.length);
    }, CYCLE_MS);
    return () => clearInterval(interval);
  }, [paused, reducedMotion]);

  useEffect(() => {
    return () => {
      if (resumeTimeoutRef.current) clearTimeout(resumeTimeoutRef.current);
    };
  }, []);

  function handleSelect(index: number) {
    setActiveIndex(index);
    setPaused(true);
    if (resumeTimeoutRef.current) clearTimeout(resumeTimeoutRef.current);
    resumeTimeoutRef.current = setTimeout(() => setPaused(false), RESUME_MS);
  }

  return {
    stages: PIPELINE_STAGES,
    activeIndex,
    active: PIPELINE_STAGES[activeIndex],
    handleSelect,
  };
}

interface PipelineChipsProps {
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function PipelineChips({ activeIndex, onSelect }: PipelineChipsProps) {
  return (
    <div className="font-mono flex flex-wrap items-center gap-1">
      {PIPELINE_STAGES.map((stage, i) => {
        const isActive = i === activeIndex;
        return (
          <span key={stage.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onSelect(i)}
              className="chip"
              data-active={isActive || undefined}
              style={
                isActive
                  ? ({
                      background: stage.color,
                      "--glow": hexToRgba(stage.color, 0.7),
                    } as CSSProperties)
                  : undefined
              }
            >
              {stage.tag}
            </button>
            {i < PIPELINE_STAGES.length - 1 && (
              <span className="separator">→</span>
            )}
          </span>
        );
      })}

      <style jsx>{`
        .chip {
          font-size: 11px;
          padding: 5px 10px;
          border-radius: 3px;
          border: 1px solid #2a2d35;
          background: transparent;
          color: inherit;
          cursor: pointer;
          transition:
            background 0.35s,
            color 0.35s,
            border-color 0.35s;
        }
        .chip[data-active] {
          color: #16181d;
          font-weight: 700;
          animation: chipGlow 1.8s ease-in-out infinite alternate;
        }
        @keyframes chipGlow {
          from {
            box-shadow: 0 0 5px 0 var(--glow);
          }
          to {
            box-shadow: 0 0 16px 2px var(--glow);
          }
        }
        .separator {
          color: #4a4f5a;
          font-size: 11px;
        }
        @media (prefers-reduced-motion: reduce) {
          .chip[data-active] {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}

export function PipelineDescriptionBand({ stage }: { stage: PipelineStage }) {
  return (
    <div
      className="description-band"
      style={{ boxShadow: `inset 3px 0 0 ${stage.color}` }}
    >
      <span className="tag font-mono" style={{ color: stage.color }}>
        {stage.tag}
      </span>{" "}
      {stage.description}

      <style jsx>{`
        .description-band {
          font-size: 11px;
          color: #8b909c;
          background: #131519;
          border-top: 1px solid #2a2d35;
          border-bottom: 1px solid #2a2d35;
          padding: 11px 28px;
          transition: box-shadow 0.35s;
        }
        .tag {
          font-weight: 700;
        }
      `}</style>
    </div>
  );
}

export function PipelineTicker() {
  const { activeIndex, active, handleSelect } = usePipelineTicker();

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 border-b border-[#2a2d35] px-7 py-3">
        <PipelineChips activeIndex={activeIndex} onSelect={handleSelect} />
      </div>
      <PipelineDescriptionBand stage={active} />
    </div>
  );
}
