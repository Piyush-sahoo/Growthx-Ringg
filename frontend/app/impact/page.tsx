"use client";

import { useEffect, useMemo, useState } from "react";
import { listCalls, type CallRecord } from "@/lib/api";

const CONVERSION_OUTCOMES = new Set(["activated_distracted", "checkout_link_sent"]);

export default function ImpactPage() {
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () =>
      listCalls()
        .then((c) => {
          setCalls(c);
          setError(null);
        })
        .catch((e) => setError((e as Error).message));
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  const stats = useMemo(() => {
    const total = calls.length;
    const completed = calls.filter((c) => c.status === "completed");
    const linksSent = calls.filter((c) => c.checkout_link_sent).length;
    const followups = calls.filter((c) => c.is_followup).length;

    const outcomeCounts = new Map<string, number>();
    for (const c of calls) {
      const key = c.outcome ?? "(none)";
      outcomeCounts.set(key, (outcomeCounts.get(key) ?? 0) + 1);
    }
    const outcomes = Array.from(outcomeCounts.entries()).sort((a, b) => b[1] - a[1]);
    const maxOutcome = outcomes.reduce((m, [, n]) => Math.max(m, n), 0);

    const converted = completed.filter(
      (c) => (c.outcome && CONVERSION_OUTCOMES.has(c.outcome)) || c.checkout_link_sent,
    ).length;
    const conversionRate = completed.length
      ? Math.round((converted / completed.length) * 100)
      : 0;

    return {
      total,
      completedCount: completed.length,
      linksSent,
      followups,
      outcomes,
      maxOutcome,
      converted,
      conversionRate,
    };
  }, [calls]);

  return (
    <main className="container wide grid" style={{ gap: 20 }}>
      <header>
        <h1 style={{ margin: 0 }}>Impact Dashboard</h1>
        <p className="muted">Outcomes, checkout links, follow-ups and called-cohort conversion.</p>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="stat-row">
        <div className="stat">
          <div className="big">{stats.total}</div>
          <div className="lbl">Total calls</div>
        </div>
        <div className="stat">
          <div className="big">{stats.linksSent}</div>
          <div className="lbl">Checkout links sent</div>
        </div>
        <div className="stat">
          <div className="big">{stats.followups}</div>
          <div className="lbl">Follow-ups</div>
        </div>
        <div className="stat">
          <div className="big">{stats.conversionRate}%</div>
          <div className="lbl">
            Cohort conversion ({stats.converted}/{stats.completedCount} completed)
          </div>
        </div>
      </section>

      <section className="card grid" style={{ gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 16 }}>Outcome distribution</h2>
        {stats.outcomes.length === 0 ? (
          <p className="muted">No calls yet.</p>
        ) : (
          <div>
            {stats.outcomes.map(([outcome, count]) => (
              <div className="bar-row" key={outcome}>
                <span style={{ textTransform: "capitalize" }}>{outcome.replace(/_/g, " ")}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${stats.maxOutcome ? (count / stats.maxOutcome) * 100 : 0}%`,
                    }}
                  />
                </div>
                <span style={{ textAlign: "right" }}>{count}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card grid" style={{ gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 16 }}>Recent calls</h2>
        {calls.length === 0 ? (
          <p className="muted">No calls yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Status</th>
                <th>Outcome</th>
                <th>Link</th>
                <th>Follow-up</th>
              </tr>
            </thead>
            <tbody>
              {calls.slice(0, 20).map((c) => (
                <tr key={c.id}>
                  <td>{c.customer_name}</td>
                  <td>
                    <span className={`badge ${c.status}`}>{c.status.replace("_", " ")}</span>
                  </td>
                  <td>{c.outcome ? c.outcome.replace(/_/g, " ") : <span className="muted">—</span>}</td>
                  <td>{c.checkout_link_sent ? "yes" : <span className="muted">—</span>}</td>
                  <td>{c.is_followup ? "yes" : <span className="muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
