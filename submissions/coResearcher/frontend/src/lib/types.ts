// Domain + API types mirroring the coResearcher backend contracts.

export type RunStatus =
  | "pending"
  | "ideating"
  | "awaiting_question_selection"
  | "reviewing_literature"
  | "designing_methodology"
  | "planning"
  | "judging"
  | "awaiting_plan_approval"
  | "completed"
  | "capped"
  | "error";

// --- Persisted (GET /runs/{id}) shapes --------------------------------------

export interface Project {
  id: string;
  brief: string;
  researcher_context?: string | null;
  own_data?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: string;
  project_id: string;
  thread_id: string;
  status: RunStatus;
  caps: Record<string, number>;
  cost_used: Record<string, number>;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Question {
  id: string;
  run_id: string;
  text: string;
  rationale?: string | null;
  tag?: string | null;
  selected: boolean;
  position: number;
  created_at: string;
}

export interface Paper {
  id: string;
  question_id: string;
  source: string;
  title: string;
  authors: string[];
  year?: number | null;
  venue?: string | null;
  doi?: string | null;
  url?: string | null;
  abstract?: string | null;
  relevance?: string | null;
  created_at: string;
}

export interface Methodology {
  id: string;
  question_id: string;
  methods: string[];
  datasets: string[];
  gaps: string[];
  created_at: string;
  updated_at: string;
}

export interface PlanDataSource {
  description?: string;
  source?: string | null;
}

export interface PlanContent {
  objective?: string;
  hypotheses?: string[];
  methods?: (string | PlanDataSource)[];
  data?: (string | PlanDataSource)[];
  risks?: string[];
  resources?: string[];
  [key: string]: unknown;
}

export interface Plan {
  id: string;
  question_id: string;
  content_json: PlanContent;
  feasibility_total?: number | null;
  rank?: number | null;
  notion_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Score {
  id: string;
  plan_id: string;
  criterion: string;
  score: number;
  weight: number;
  justification?: string | null;
  total?: number | null;
  created_at: string;
}

export interface RankedPlan {
  plan: Plan;
  scores: Score[];
}

export interface RunResults {
  run: Run;
  project: Project;
  questions: Question[];
  papers: Paper[];
  methodologies: Methodology[];
  ranked_plans: RankedPlan[];
}

// --- Graph-state shapes embedded in SSE interrupt payloads ------------------

export interface GateQuestion {
  id: string;
  text: string;
  rationale: string;
  tag: string;
  selected: boolean;
}

export interface GatePlan {
  id: string;
  question_id: string;
  content: PlanContent;
}

export interface GateCriterionScore {
  criterion: string;
  score: number;
  weight: number;
  justification: string;
}

export interface GateRankedPlan {
  plan: GatePlan;
  scores: GateCriterionScore[];
  total: number;
  rank: number;
}

export type InterruptPayload =
  | { gate: "question_selection"; questions: GateQuestion[] }
  | { gate: "plan_approval"; ranked_plans: GateRankedPlan[] };

// --- SSE event payloads -----------------------------------------------------

export interface SnapshotData {
  status: RunStatus;
  done: boolean;
  interrupt: InterruptPayload | null;
}

// Literature source -> short failure reason (e.g. "rate limited (HTTP 429)").
export type SourceHealth = Record<string, string>;

export interface NodeData {
  node: string;
  status?: RunStatus | null;
  logs: string[];
  source_health?: SourceHealth;
}

export interface CostData {
  tokens: number;
  cost_usd: number;
  tool_calls: number;
}

export interface CompletedData {
  status: RunStatus;
  approved_plan_id?: string | null;
}

export interface ErrorData {
  message: string;
}

// --- Requests / responses ---------------------------------------------------

export interface CapsOverride {
  max_questions?: number;
  max_papers_per_question?: number;
  max_tool_calls?: number;
  token_ceiling?: number;
  cost_ceiling_usd?: number;
  wall_clock_seconds?: number;
}

export interface CreateRunRequest {
  brief: string;
  researcher_context?: string;
  own_data?: string;
  caps?: CapsOverride;
  sources?: string[];
}

export interface CreateRunResponse {
  run_id: string;
  thread_id: string;
  status: RunStatus;
}

export interface QuestionSelectionResume {
  selected_ids?: string[];
  selected_indexes?: number[];
  edits?: { id: string; text?: string; rationale?: string; tag?: string }[];
}

export interface PlanApprovalResume {
  approved_plan_id?: string;
  approved_index?: number;
}

export type ResumePayload = QuestionSelectionResume | PlanApprovalResume;

export interface ExportResponse {
  plan_id: string;
  notion_url: string;
}
