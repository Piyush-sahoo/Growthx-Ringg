// Typed client for the FastAPI backend.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type CallStatus = "queued" | "in_progress" | "completed" | "failed";

export interface CallRecord {
  id: string;
  customer_name: string;
  phone_number: string;
  custom_args_values: Record<string, unknown>;
  status: CallStatus;
  ringg_call_id: string | null;
  transcript: string | null;
  recording_url: string | null;
  analysis: Record<string, unknown> | null;
  outcome: string | null;
  actions: Array<Record<string, unknown>>;
  checkout_link_sent: boolean;
  current_node_id?: string | null;
  workflow_id?: string | null;
  is_followup?: boolean;
  parent_call_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutboundCallRequest {
  customer_name: string;
  phone_number: string;
  custom_args_values?: Record<string, unknown>;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function listCalls(): Promise<CallRecord[]> {
  return handle<CallRecord[]>(await fetch(`${API_URL}/calls`, { cache: "no-store" }));
}

export async function createCall(payload: OutboundCallRequest): Promise<CallRecord> {
  return handle<CallRecord>(
    await fetch(`${API_URL}/calls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

/* ------------------------------------------------------------------ *
 * Workflows (S7–S10)
 * ------------------------------------------------------------------ */

export type WorkflowNodeType = "call" | "tool" | "terminal";

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  label: string;
  outcomes: string[];
  tool?: string | null;
  agent_id?: string | null;
}

export interface WorkflowEdge {
  source: string;
  target: string;
  /** The outcome that causes this edge to be taken. */
  on: string;
}

export interface WorkflowGraph {
  id: string;
  name: string;
  entry: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface TemplateSummary {
  id: string;
  name: string;
}

export interface DeployedAgent {
  node_id: string;
  agent_id: string;
  created?: boolean;
  reused?: boolean;
  subscribed?: boolean;
  label?: string;
  [k: string]: unknown;
}

export interface DeployResult {
  deployment: { agents: DeployedAgent[] };
  graph: WorkflowGraph;
}

export interface GenerateResult {
  graph: WorkflowGraph;
}

export async function listTemplates(): Promise<TemplateSummary[]> {
  return handle<TemplateSummary[]>(
    await fetch(`${API_URL}/workflows/templates`, { cache: "no-store" }),
  );
}

export async function getTemplate(id: string): Promise<WorkflowGraph> {
  return handle<WorkflowGraph>(
    await fetch(`${API_URL}/workflows/templates/${encodeURIComponent(id)}`, {
      cache: "no-store",
    }),
  );
}

export async function deployWorkflow(
  payload: { template_id: string } | { graph: WorkflowGraph },
): Promise<DeployResult> {
  return handle<DeployResult>(
    await fetch(`${API_URL}/workflows/deploy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function generateWorkflow(payload: {
  prompt: string;
  base_template_id?: string;
}): Promise<GenerateResult> {
  return handle<GenerateResult>(
    await fetch(`${API_URL}/workflows/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function getCredits(): Promise<{ credits: number }> {
  return handle<{ credits: number }>(
    await fetch(`${API_URL}/workflows/credits`, { cache: "no-store" }),
  );
}
