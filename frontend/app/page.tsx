"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCredits, listAgents, listRinggCalls } from "@/lib/api";

const HOW = [
  ["01 · Describe", "Brainstorm the flow in plain language or pick a template — it renders as a live graph."],
  ["02 · Deploy", "One click creates real Ringg assistants per call-step and wires their webhooks."],
  ["03 · Run & measure", "Place the call; branches, tools and follow-ups fire automatically; impact shows live."],
];

const FEATURES = [
  ["Multi-agent workflows", "Check-in → decision-maker → day-before recall → win-back, each a real Ringg agent."],
  ["Three-layer memory", "Now / before / business-rules survive every handoff — the recall opens with the prior promise."],
  ["Tools after the call", "Checkout link, WhatsApp, escalation, PDF, callback — pre-call, on-call and post-call."],
  ["Outcomes, not features", "Every call records a structured outcome and rolls up into trial-to-paid impact."],
];

export default function Landing() {
  const [stats, setStats] = useState<{ agents: number; calls: number; credits: number | null }>({
    agents: 0,
    calls: 0,
    credits: null,
  });

  useEffect(() => {
    Promise.all([
      listAgents().catch(() => []),
      listRinggCalls().catch(() => []),
      getCredits().catch(() => ({ credits: 0 })),
    ]).then(([a, c, cr]) => setStats({ agents: a.length, calls: c.length, credits: cr.credits }));
  }, []);

  return (
    <main className="container grid landing" style={{ gap: 44 }}>
      <section className="landing-hero reveal">
        <span className="eyebrow">GrowthX × Ringg AI · Voice AI Buildathon</span>
        <h1>
          Ringg handles the call.
          <br />
          You handle <em>everything after</em>.
        </h1>
        <p className="lede">
          FlowForge turns one Ringg voice agent into a multi-agent workflow — it branches on what
          the customer says, fires the right tools, and carries memory across calls. Describe it in
          plain language, deploy real agents, and watch the outcome move.
        </p>
        <div className="cta-row">
          <Link href="/console" className="btn">
            Open the console →
          </Link>
          <Link href="/builder" className="btn ghost">
            Design a workflow
          </Link>
        </div>
        <div className="stat-row" style={{ marginTop: 6 }}>
          <div className="stat reveal">
            <div className="big">{stats.agents}</div>
            <div className="lbl">Live agents</div>
          </div>
          <div className="stat reveal">
            <div className="big">{stats.calls}</div>
            <div className="lbl">Calls handled</div>
          </div>
          <div className="stat reveal">
            <div className="big">{stats.credits ?? "—"}</div>
            <div className="lbl">Ringg credits</div>
          </div>
        </div>
      </section>

      <section className="grid" style={{ gap: 16 }}>
        <span className="eyebrow">How it works</span>
        <div className="feature-grid">
          {HOW.map(([t, d]) => (
            <div key={t} className="card">
              <h3>{t}</h3>
              <p className="muted">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid" style={{ gap: 16 }}>
        <span className="eyebrow">What makes it different</span>
        <div className="feature-grid">
          {FEATURES.map(([t, d]) => (
            <div key={t} className="card">
              <h3>{t}</h3>
              <p className="muted">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="muted" style={{ textAlign: "center", paddingTop: 12 }}>
        FlowForge · built on Ringg AI for the GrowthX Voice AI Buildathon
      </footer>
    </main>
  );
}
