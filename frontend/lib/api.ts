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
