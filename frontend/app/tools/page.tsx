"use client";

import { useEffect, useState } from "react";
import {
  getAgentTools,
  getToolCatalog,
  listAgents,
  type AgentSummary,
  type AgentTools,
  type CatalogGroup,
  type ToolItem,
} from "@/lib/api";

function EnabledDot({ on }: { on?: boolean | null }) {
  return (
    <span className={`badge ${on ? "completed" : "queued"}`}>{on ? "enabled" : "off"}</span>
  );
}

function ToolRow({ t }: { t: ToolItem }) {
  return (
    <div className="tool-row">
      <div>
        <span className="tool-name">{t.name}</span>
        {t.type && <span className="tool-type mono"> {t.type}</span>}
        {(t.url || t.does) && <div className="muted" style={{ marginTop: 2 }}>{t.url || t.does}</div>}
      </div>
      {"enabled" in t && t.enabled !== undefined && <EnabledDot on={t.enabled} />}
    </div>
  );
}

const PHASES: [keyof AgentTools, string][] = [
  ["pre_call", "Pre-call"],
  ["on_call", "On-call"],
  ["post_call", "Post-call"],
  ["embedded", "Embedded (web)"],
  ["available", "Available (toggle on)"],
];

export default function ToolsPage() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [agentId, setAgentId] = useState("");
  const [tools, setTools] = useState<AgentTools | null>(null);
  const [catalog, setCatalog] = useState<Record<string, CatalogGroup>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAgents()
      .then((a) => {
        setAgents(a);
        if (a[0]) setAgentId(a[0].id);
      })
      .catch((e) => setError((e as Error).message));
    getToolCatalog()
      .then(setCatalog)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!agentId) return;
    setTools(null);
    getAgentTools(agentId)
      .then(setTools)
      .catch((e) => setError((e as Error).message));
  }, [agentId]);

  return (
    <main className="container wide grid" style={{ gap: 24 }}>
      <header className="hero reveal">
        <span className="eyebrow">Agent toolbox</span>
        <h1>
          Every tool, <em>per agent</em>.
        </h1>
        <p className="lede">
          What each agent can actually do — pre-call, on-call, and post-call — read live, plus the
          full catalog of tools you can attach.
        </p>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="card reveal">
        <h2>Attached to this agent</h2>
        <div style={{ maxWidth: 520 }}>
          <label>Agent</label>
          <select className="select" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
            {agents.length === 0 && <option>Loading…</option>}
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>

        {tools && (
          <div className="grid" style={{ gap: 18, marginTop: 18 }}>
            <span className="muted mono">
              tool-call logs in analytics: {tools.tool_call_logs ? "on" : "off"}
            </span>
            <div className="tool-cols">
              {PHASES.map(([key, label]) => {
                const list = tools[key] as ToolItem[];
                return (
                  <div key={key} className="tool-col">
                    <span className="eyebrow">{label}</span>
                    {list.length === 0 ? (
                      <p className="muted" style={{ marginTop: 8 }}>none</p>
                    ) : (
                      list.map((t, i) => <ToolRow key={i} t={t} />)
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      <section className="card reveal">
        <h2>Tool catalog</h2>
        <div className="tool-cols">
          {Object.entries(catalog).map(([id, group]) => (
            <div key={id} className="tool-col">
              <span className="eyebrow">{group.group}</span>
              {group.tools.map((t, i) => (
                <ToolRow key={i} t={t} />
              ))}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
