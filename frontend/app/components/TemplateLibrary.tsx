"use client";

import { useEffect, useState } from "react";
import { listTemplates, type TemplateSummary } from "@/lib/api";

export default function TemplateLibrary({
  selectedId,
  onSelect,
}: {
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTemplates()
      .then(setTemplates)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <section className="card grid" style={{ gap: 12 }}>
      <h2 style={{ margin: 0, fontSize: 16 }}>Template library</h2>
      {error && <p className="error">{error}</p>}
      {!error && templates.length === 0 && <p className="muted">No templates available.</p>}
      <div className="grid" style={{ gap: 8 }}>
        {templates.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`template-item${selectedId === t.id ? " active" : ""}`}
            onClick={() => onSelect(t.id)}
          >
            {t.name}
            <span className="tid">{t.id}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
