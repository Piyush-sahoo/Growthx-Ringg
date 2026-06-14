"use client";

import { useState } from "react";
import { generateWorkflow, type WorkflowGraph } from "@/lib/api";

interface Msg {
  role: "user" | "assistant" | "system";
  text: string;
}

export default function BrainstormChat({
  baseTemplateId,
  onGraph,
}: {
  baseTemplateId: string | null;
  onGraph: (graph: WorkflowGraph) => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "system",
      text: "Describe the workflow you want. I'll draft a graph you can tweak and deploy.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || loading) return;
    setMessages((m) => [...m, { role: "user", text: prompt }]);
    setInput("");
    setLoading(true);
    try {
      const { graph } = await generateWorkflow({
        prompt,
        base_template_id: baseTemplateId ?? undefined,
      });
      onGraph(graph);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: `Drafted "${graph.name}" — ${graph.nodes.length} nodes, ${graph.edges.length} edges. Rendered on the canvas. Refine it or deploy.`,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Generation failed: ${(err as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card grid" style={{ gap: 12 }}>
      <h2 style={{ margin: 0, fontSize: 16 }}>Brainstorm</h2>
      <div className="chat-log">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.text}
          </div>
        ))}
        {loading && <div className="chat-msg assistant">Generating…</div>}
      </div>
      <form onSubmit={send} className="grid" style={{ gap: 8 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={3}
          placeholder="e.g. Call trial users, if they pick up qualify them, send a checkout link if interested, otherwise schedule a follow-up."
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? "Generating…" : "Generate workflow"}
        </button>
      </form>
    </section>
  );
}
