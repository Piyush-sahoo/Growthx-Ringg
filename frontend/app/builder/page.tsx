"use client";

import { useCallback, useState } from "react";
import { getTemplate, type WorkflowGraph } from "@/lib/api";
import WorkflowVisualizer from "../components/WorkflowVisualizer";
import TemplateLibrary from "../components/TemplateLibrary";
import DeployPanel from "../components/DeployPanel";
import BrainstormChat from "../components/BrainstormChat";

export default function BuilderPage() {
  const [graph, setGraph] = useState<WorkflowGraph | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectTemplate = useCallback(async (id: string) => {
    setSelectedId(id);
    setError(null);
    try {
      const g = await getTemplate(id);
      setGraph(g);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const onGenerated = useCallback((g: WorkflowGraph) => {
    setGraph(g);
    setSelectedId(null);
  }, []);

  return (
    <main className="container wide grid" style={{ gap: 20 }}>
      <header className="hero reveal">
        <span className="eyebrow">Workflow architect</span>
        <h1>
          Describe it. <em>Deploy</em> it.
        </h1>
        <p className="lede">
          Pick a template or brainstorm a new flow in plain language, watch it render as a
          live graph, then deploy real Ringg agents. The canvas lights up the taken path
          from the most recent call.
        </p>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="builder-grid">
        <div className="grid" style={{ gap: 16 }}>
          <TemplateLibrary selectedId={selectedId} onSelect={selectTemplate} />
        </div>

        <div className="grid" style={{ gap: 16 }}>
          <WorkflowVisualizer graph={graph} />
          <DeployPanel graph={graph} />
        </div>

        <div className="grid" style={{ gap: 16 }}>
          <BrainstormChat baseTemplateId={selectedId} onGraph={onGenerated} />
        </div>
      </div>
    </main>
  );
}
