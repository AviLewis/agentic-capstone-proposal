// Typed API client for the coResearcher backend.

import type {
  CreateRunRequest,
  CreateRunResponse,
  ExportResponse,
  ResumePayload,
  RunResults,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function apiMessage(body: unknown, fallback: string): string {
  if (
    body &&
    typeof body === "object" &&
    "error" in body &&
    body.error &&
    typeof body.error === "object" &&
    "message" in body.error &&
    typeof (body.error as { message: unknown }).message === "string"
  ) {
    return (body.error as { message: string }).message;
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text().catch(() => undefined);
    }
    throw new ApiError(
      apiMessage(body, `Request to ${path} failed (${res.status})`),
      res.status,
      body,
    );
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),

  createRun: (payload: CreateRunRequest) =>
    request<CreateRunResponse>("/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getRun: (runId: string) => request<RunResults>(`/runs/${runId}`),

  resumeRun: (runId: string, resume: ResumePayload) =>
    request<{ run_id: string; status: string }>(`/runs/${runId}/resume`, {
      method: "POST",
      body: JSON.stringify({ resume }),
    }),

  exportToNotion: (runId: string, planId?: string) =>
    request<ExportResponse>(`/runs/${runId}/export`, {
      method: "POST",
      body: JSON.stringify({ plan_id: planId ?? null }),
    }),

  streamUrl: (runId: string) => `${API_BASE_URL}/runs/${runId}/stream`,
};
