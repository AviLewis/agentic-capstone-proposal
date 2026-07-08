import Link from "next/link";
import type { CostData, RunStatus } from "@/lib/types";

export type DisplayStatus = RunStatus | "connecting" | "running";

function statusBadge(status: DisplayStatus) {
  if (status === "completed") {
    return { icon: "✓", color: "#4ec97a", bg: "rgba(78,201,122,.1)" };
  }
  if (status === "error" || status === "capped") {
    return { icon: "✕", color: "#e2716b", bg: "rgba(226,113,107,.12)" };
  }
  if (
    status === "awaiting_question_selection" ||
    status === "awaiting_plan_approval"
  ) {
    return { icon: "▮", color: "#e8b04b", bg: "rgba(232,176,75,.12)" };
  }
  if (status === "connecting" || status === "pending") {
    return { icon: "·", color: "#8b909c", bg: "rgba(109,114,128,.15)" };
  }
  return { icon: "▶", color: "#4ec97a", bg: "rgba(78,201,122,.1)" };
}

interface ConsoleTopBarProps {
  runId: string;
  cost: CostData | null;
  status: DisplayStatus;
}

export function ConsoleTopBar({ runId, cost, status }: ConsoleTopBarProps) {
  const badge = statusBadge(status);

  return (
    <div className="font-mono flex items-center justify-between gap-4 border-b border-[#2a2d35] px-7 py-3.5">
      <div className="flex items-center gap-3.5">
        <Link href="/" className="text-sm font-bold text-[#e8b04b]">
          co·researcher
        </Link>
        <span className="text-[11px] text-[#6d7280]">
          run/{runId.slice(0, 8)}
        </span>
      </div>
      <div className="flex items-center gap-5 text-[11px] text-[#8b909c]">
        <span>
          tok{" "}
          <span className="text-[#e8e6e1]">
            {(cost?.tokens ?? 0).toLocaleString()}
          </span>
        </span>
        <span>
          usd{" "}
          <span className="text-[#e8e6e1]">
            {(cost?.cost_usd ?? 0).toFixed(4)}
          </span>
        </span>
        <span>
          calls <span className="text-[#e8e6e1]">{cost?.tool_calls ?? 0}</span>
        </span>
        <span
          className="rounded px-2.5 py-1"
          style={{ color: badge.color, background: badge.bg }}
        >
          {badge.icon} {status}
        </span>
      </div>
    </div>
  );
}
