"use client";

import { useState } from "react";
import {
  deployWorkflow,
  type DeployResult,
  type WorkflowGraph,
} from "@/lib/api";

export default function DeployPanel({ graph }: { graph: WorkflowGraph | null }) {
  const [result, setResult] = useState<DeployResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function deploy() {
    if (!graph) return;
    setLoading(true);
    setError(null);
    try {
      // Prefer template_id when the graph corresponds to a known template;
      // otherwise deploy the raw graph (e.g. a generated workflow).
      const payload = graph.id
        ? { template_id: graph.id }
        : { graph };
      const res = await deployWorkflow(payload);
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card grid" style={{ gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 16, flex: 1 }}>Deploy</h2>
        <button type="button" onClick={deploy} disabled={!graph || loading}>
          {loading ? "Deploying…" : "Deploy workflow"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="deploy-panel">
          <p className="muted" style={{ margin: "0 0 8px" }}>
            {result.deployment.agents.length} agent(s) provisioned.
          </p>
          <table>
            <thead>
              <tr>
                <th>Node</th>
                <th>Agent</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {result.deployment.agents.map((a, i) => (
                <tr key={a.agent_id ?? i}>
                  <td>{a.label ?? a.node_id ?? "—"}</td>
                  <td style={{ fontSize: 12 }}>{a.agent_id}</td>
                  <td>
                    {a.created && <span className="badge completed">created</span>}
                    {a.reused && <span className="badge queued">reused</span>}{" "}
                    {a.subscribed && <span className="badge completed">subscribed</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
