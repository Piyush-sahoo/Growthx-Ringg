"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createCall,
  getAgentVariables,
  listAgents,
  listRinggCalls,
  type AgentSummary,
  type RinggCall,
} from "@/lib/api";

// Variables auto-filled from the name/phone fields — hidden from the dynamic form.
const AUTO_VARS = new Set(["callee_name", "mobile_number", "customer_name", "phone_number"]);

const VAR_HINTS: Record<string, string> = {
  trial_id: "T-88412",
  days_left: "3",
  accounts_connected: "3",
  reports_sent: "2",
  plan_fit: "Studio",
  decision_owner: "co-founder (rubber stamp)",
  last_promise: "none (first call)",
  memory_summary: "First outreach — 3 accounts connected, 2 reports sent",
  upgrade_link: "https://app.reportzen.io/up/asha",
  amount: "499",
  retry_link: "https://pay.example/retry",
};

const humanize = (s: string) => s.replace(/_/g, " ");

export default function Home() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [agentId, setAgentId] = useState<string>("");
  const [variables, setVariables] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [vals, setVals] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [calls, setCalls] = useState<RinggCall[]>([]);
  const [scopeAll, setScopeAll] = useState(true);

  // Load agents once.
  useEffect(() => {
    listAgents()
      .then((a) => {
        setAgents(a);
        if (a.length && !agentId) setAgentId(a[0].id);
      })
      .catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load the selected agent's variables (drives the dynamic fields).
  useEffect(() => {
    if (!agentId) return;
    getAgentVariables(agentId)
      .then((v) => setVariables(v.filter((x) => !AUTO_VARS.has(x))))
      .catch(() => setVariables([]));
  }, [agentId]);

  const refresh = useCallback(async () => {
    try {
      setCalls(await listRinggCalls(scopeAll ? undefined : agentId));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [scopeAll, agentId]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 6000);
    return () => clearInterval(t);
  }, [refresh]);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === agentId),
    [agents, agentId],
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const custom_args_values: Record<string, string> = {};
    for (const k of variables) if (vals[k]?.trim()) custom_args_values[k] = vals[k].trim();
    try {
      await createCall({
        customer_name: name,
        phone_number: phone,
        agent_id: agentId || undefined,
        custom_args_values,
      });
      setName("");
      setPhone("");
      setVals({});
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container grid" style={{ gap: 28 }}>
      <header className="hero reveal">
        <span className="eyebrow">Live console · Ringg AI</span>
        <h1>
          Place the call.<br />Watch it <em>think</em>.
        </h1>
        <p className="lede">
          Pick an agent — the form adapts to <em>its</em> variables. Place an outbound call,
          then watch every agent&apos;s real calls, transcripts and recordings stream in.
        </p>
      </header>

      <section className="card reveal">
        <h2>New outbound call</h2>
        <form className="grid" onSubmit={onSubmit}>
          <div>
            <label>Agent</label>
            <select
              className="select"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
            >
              {agents.length === 0 && <option value="">Loading agents…</option>}
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} {a.type ? `· ${a.type}` : ""}
                </option>
              ))}
            </select>
            {selectedAgent && (
              <p className="muted mono" style={{ marginTop: 6 }}>
                {selectedAgent.id}
              </p>
            )}
          </div>

          <div className="row">
            <div>
              <label>Customer name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Asha Rao"
                required
              />
            </div>
            <div>
              <label>Phone number</label>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+919812345678"
                required
              />
            </div>
          </div>

          {variables.length > 0 && (
            <div className="grid" style={{ gap: 14 }}>
              <span className="eyebrow">Agent variables · {selectedAgent?.name}</span>
              <div className="var-grid">
                {variables.map((v) => (
                  <div key={v}>
                    <label>{humanize(v)}</label>
                    <input
                      value={vals[v] ?? ""}
                      onChange={(e) => setVals((s) => ({ ...s, [v]: e.target.value }))}
                      placeholder={VAR_HINTS[v] ?? humanize(v)}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <button type="submit" disabled={loading || !agentId}>
              {loading ? "Placing call…" : "Place call"}
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      <section className="card reveal">
        <div
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <h2 style={{ margin: 0 }}>Call history</h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              className={scopeAll ? undefined : "secondary"}
              onClick={() => setScopeAll(true)}
              style={{ padding: "6px 12px", fontSize: 12 }}
            >
              All agents
            </button>
            <button
              type="button"
              className={scopeAll ? "secondary" : undefined}
              onClick={() => setScopeAll(false)}
              style={{ padding: "6px 12px", fontSize: 12 }}
            >
              This agent
            </button>
          </div>
        </div>

        {calls.length === 0 ? (
          <p className="muted" style={{ marginTop: 14 }}>
            No calls yet. Place one above.
          </p>
        ) : (
          <table style={{ marginTop: 14 }}>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Phone</th>
                <th>Agent</th>
                <th>Status</th>
                <th>Dur</th>
                <th>Transcript</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id}>
                  <td>{c.name || <span className="muted">—</span>}</td>
                  <td className="mono">{c.to_number}</td>
                  <td>
                    <span className="muted">{c.agent_name || "—"}</span>
                  </td>
                  <td>
                    <span className={`badge ${c.status === "completed" ? "completed" : "in_progress"}`}>
                      {c.status || "—"}
                    </span>
                  </td>
                  <td className="mono">{c.duration ? `${Math.round(c.duration)}s` : "—"}</td>
                  <td>
                    {c.transcript ? (
                      <span>{c.transcript.slice(0, 120)}</span>
                    ) : (
                      <span className="muted">no transcript</span>
                    )}
                    {c.recording_url && (
                      <>
                        {" "}
                        <a href={c.recording_url} target="_blank" rel="noreferrer">
                          ▶ rec
                        </a>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
