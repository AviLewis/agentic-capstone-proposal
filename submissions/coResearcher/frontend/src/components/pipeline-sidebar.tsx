import type { RunStatus } from "@/lib/types";
import type { DisplayStatus } from "@/components/console-topbar";

interface PipelineStageDef {
  key: string;
  label: string;
  status: RunStatus;
  gate: boolean;
  runningHint: string;
}

const STAGES: PipelineStageDef[] = [
  {
    key: "ideator",
    label: "ideator",
    status: "ideating",
    gate: false,
    runningHint: "generating and deduping candidate questions",
  },
  {
    key: "question_selection",
    label: "question selection",
    status: "awaiting_question_selection",
    gate: true,
    runningHint: "choose which questions proceed",
  },
  {
    key: "literature_review",
    label: "literature review",
    status: "reviewing_literature",
    gate: false,
    runningHint: "plan → act → observe · openalex, arxiv, semantic scholar",
  },
  {
    key: "methodology",
    label: "methodology",
    status: "designing_methodology",
    gate: false,
    runningHint: "designing testable methods per question",
  },
  {
    key: "research_plan",
    label: "research plan",
    status: "planning",
    gate: false,
    runningHint: "drafting plans with methods & risks",
  },
  {
    key: "judge",
    label: "judge",
    status: "judging",
    gate: false,
    runningHint: "scoring plans on 5 weighted criteria",
  },
  {
    key: "plan_approval",
    label: "plan approval",
    status: "awaiting_plan_approval",
    gate: true,
    runningHint: "approve one plan to finish",
  },
];

function currentStageIndex(status: DisplayStatus): number {
  if (status === "connecting" || status === "running" || status === "pending") {
    return -1;
  }
  return STAGES.findIndex((s) => s.status === status);
}

interface PipelineSidebarProps {
  status: DisplayStatus;
  costUsd: number;
  costCeilingUsd?: number | null;
}

export function PipelineSidebar({
  status,
  costUsd,
  costCeilingUsd,
}: PipelineSidebarProps) {
  const currentIndex =
    status === "completed" ? STAGES.length : currentStageIndex(status);

  const pct =
    costCeilingUsd && costCeilingUsd > 0
      ? Math.min(100, Math.round((costUsd / costCeilingUsd) * 100))
      : 0;

  return (
    <div className="font-mono flex w-[400px] flex-none flex-col gap-0.5 border-r border-[#2a2d35] bg-[#131519] px-[26px] py-6">
      <p className="mb-4 text-[10px] tracking-[0.14em] text-[#6d7280]">
        PIPELINE
      </p>

      {STAGES.map((stage, i) => {
        const isCurrent = i === currentIndex;
        const isDone = i < currentIndex;
        const marker = isDone
          ? "[done]"
          : isCurrent
            ? stage.gate
              ? "[gate]"
              : "[run·]"
            : "[wait]";
        const markerColor = isDone
          ? "#4ec97a"
          : isCurrent
            ? stage.gate
              ? "#e8b04b"
              : "#4ec97a"
            : "#6d7280";
        const labelColor = isDone
          ? "#e8e6e1"
          : isCurrent
            ? stage.gate
              ? "#e8b04b"
              : "#4ec97a"
            : "#e8e6e1";

        return (
          <div
            key={stage.key}
            className="flex gap-3 rounded-md py-2.5"
            style={
              isCurrent
                ? {
                    background: stage.gate
                      ? "rgba(232,176,75,.07)"
                      : "rgba(78,201,122,.07)",
                    margin: "0 -12px",
                    padding: "9px 12px",
                  }
                : { opacity: isDone ? 1 : 0.45 }
            }
          >
            <span className="flex-none" style={{ color: markerColor }}>
              {marker}
            </span>
            <div>
              <p className="text-[12.5px]" style={{ color: labelColor }}>
                {stage.label}
              </p>
              {isCurrent && (
                <p className="mt-0.5 text-[11px] leading-relaxed text-[#8b909c]">
                  {stage.runningHint}
                </p>
              )}
            </div>
          </div>
        );
      })}

      <div className="mt-auto border-t border-[#2a2d35] pt-5">
        <div className="mb-1.5 flex justify-between text-[10.5px] text-[#6d7280]">
          <span>COST CEILING</span>
          <span className="text-[#8b909c]">
            ${costUsd.toFixed(2)}
            {costCeilingUsd ? ` / $${costCeilingUsd.toFixed(2)}` : ""}
          </span>
        </div>
        <div className="h-1 rounded-full bg-[#2a2d35]">
          <div
            className="h-1 rounded-full bg-[#e8b04b]"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
