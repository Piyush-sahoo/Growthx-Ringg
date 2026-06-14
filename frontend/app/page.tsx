"use client";

import { useCallback, useEffect, useState } from "react";
import { createCall, listCalls, type CallRecord } from "@/lib/api";

export default function Home() {
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [vars, setVars] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setCalls(await listCalls());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    let custom_args_values: Record<string, unknown> = {};
    if (vars.trim()) {
      try {
        custom_args_values = JSON.parse(vars);
      } catch {
        setError("Variables must be valid JSON, e.g. {\"plan\":\"Pro\"}");
        setLoading(false);
        return;
      }
    }
    try {
      await createCall({ customer_name: name, phone_number: phone, custom_args_values });
      setName("");
      setPhone("");
      setVars("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container grid" style={{ gap: 28 }}>
      <header>
        <h1 style={{ margin: 0 }}>Voice Agent Console</h1>
        <p className="muted">
          GrowthX × Ringg AI — trigger an outbound call, then watch the transcript and
          analysis land via webhook.
        </p>
      </header>

      <section className="card">
        <h2 style={{ marginTop: 0, fontSize: 18 }}>New outbound call</h2>
        <form className="grid" onSubmit={onSubmit}>
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
          <div>
            <label>Variables (JSON, optional) — maps to @{`{{variable}}`} in your prompt</label>
            <textarea
              value={vars}
              onChange={(e) => setVars(e.target.value)}
              rows={3}
              placeholder='{"plan":"Pro","amount":"499","retry_link":"https://..."}'
            />
          </div>
          <div>
            <button type="submit" disabled={loading}>
              {loading ? "Placing call…" : "Place call"}
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Call history</h2>
        {calls.length === 0 ? (
          <p className="muted">No calls yet. Place one above.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Outcome / actions</th>
                <th>Transcript</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id}>
                  <td>{c.customer_name}</td>
                  <td>{c.phone_number}</td>
                  <td>
                    <span className={`badge ${c.status}`}>{c.status.replace("_", " ")}</span>
                  </td>
                  <td>
                    {c.outcome ? (
                      <span>{c.outcome.replace(/_/g, " ")}</span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                    {c.checkout_link_sent && (
                      <>
                        {" "}
                        <span className="badge completed">link sent</span>
                      </>
                    )}
                  </td>
                  <td>
                    {c.transcript ? (
                      <span>{c.transcript.slice(0, 140)}</span>
                    ) : (
                      <span className="muted">waiting for webhook…</span>
                    )}
                    {c.recording_url && (
                      <>
                        {" "}
                        <a href={c.recording_url} target="_blank" rel="noreferrer">
                          recording
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
