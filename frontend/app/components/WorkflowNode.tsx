"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { WorkflowNodeType } from "@/lib/api";

export interface WorkflowNodeData {
  label: string;
  kind: WorkflowNodeType;
  tool?: string | null;
  agentId?: string | null;
  outcomes: string[];
  active?: boolean;
  [k: string]: unknown;
}

const KIND_LABEL: Record<WorkflowNodeType, string> = {
  call: "Call",
  tool: "Tool",
  terminal: "Terminal",
};

export default function WorkflowNode({ data }: NodeProps) {
  const d = data as WorkflowNodeData;
  return (
    <div className={`wf-node ${d.kind}${d.active ? " active" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="wf-head">
        <span className="wf-dot" />
        {KIND_LABEL[d.kind]}
      </div>
      <div className="wf-body">
        {d.label}
        {d.kind === "tool" && d.tool && <div className="wf-sub">tool: {d.tool}</div>}
        {d.agentId && <div className="wf-sub">agent: {d.agentId}</div>}
        {d.outcomes.length > 0 && (
          <div className="wf-sub">→ {d.outcomes.join(", ")}</div>
        )}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
