"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  CompletedData,
  CostData,
  ErrorData,
  InterruptPayload,
  NodeData,
  ResumePayload,
  RunStatus,
  SnapshotData,
} from "@/lib/types";

export interface RunStreamState {
  status: RunStatus | "connecting" | "running";
  nodes: NodeData[];
  cost: CostData | null;
  gate: InterruptPayload | null;
  completed: boolean;
  approvedPlanId: string | null;
  error: string | null;
}

const INITIAL: RunStreamState = {
  status: "connecting",
  nodes: [],
  cost: null,
  gate: null,
  completed: false,
  approvedPlanId: null,
  error: null,
};

const EVENT_NAMES = [
  "snapshot",
  "node",
  "cost",
  "interrupt",
  "completed",
  "error",
] as const;

/**
 * Subscribes to a run's SSE stream. Closes the connection on any terminal event
 * (interrupt / completed / error / done snapshot) to avoid EventSource's
 * auto-reconnect loop, and reconnects on demand after a HITL resume.
 */
export function useRunStream(runId: string) {
  const [state, setState] = useState<RunStreamState>(INITIAL);
  const [streamKey, setStreamKey] = useState(0);
  const resolvedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const source = new EventSource(api.streamUrl(runId));

    const handle = (name: string, raw: string) => {
      let data: unknown;
      try {
        data = JSON.parse(raw);
      } catch {
        return;
      }

      if (name === "snapshot") {
        const snap = data as SnapshotData;
        setState((s) => ({ ...s, status: snap.status }));
        if (snap.interrupt && !resolvedRef.current.has(snap.interrupt.gate)) {
          setState((s) => ({ ...s, gate: snap.interrupt }));
        }
        if (snap.done) {
          setState((s) => ({ ...s, completed: true }));
          source.close();
        }
      } else if (name === "node") {
        const node = data as NodeData;
        setState((s) => ({
          ...s,
          nodes: [...s.nodes, node],
          status: node.status ?? s.status,
        }));
      } else if (name === "cost") {
        setState((s) => ({ ...s, cost: data as CostData }));
      } else if (name === "interrupt") {
        const payload = (data as { value: InterruptPayload }).value;
        if (!resolvedRef.current.has(payload.gate)) {
          setState((s) => ({ ...s, gate: payload }));
        }
        source.close();
      } else if (name === "completed") {
        const done = data as CompletedData;
        setState((s) => ({
          ...s,
          completed: true,
          approvedPlanId: done.approved_plan_id ?? null,
          status: done.status,
          gate: null,
        }));
        source.close();
      } else if (name === "error") {
        setState((s) => ({ ...s, error: (data as ErrorData).message }));
        source.close();
      }
    };

    for (const name of EVENT_NAMES) {
      source.addEventListener(name, (e) =>
        handle(name, (e as MessageEvent).data),
      );
    }
    // Server closes the stream after terminal/snapshot; stop auto-reconnect.
    source.onerror = () => source.close();

    return () => source.close();
  }, [runId, streamKey]);

  const resume = useCallback(
    async (gate: string, payload: ResumePayload) => {
      resolvedRef.current.add(gate);
      setState((s) => ({ ...s, gate: null, status: "running" }));
      await api.resumeRun(runId, payload);
      setStreamKey((k) => k + 1);
    },
    [runId],
  );

  return { ...state, resume };
}
