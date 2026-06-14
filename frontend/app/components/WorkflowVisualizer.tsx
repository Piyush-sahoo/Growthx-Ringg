"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { listCalls, type CallRecord, type WorkflowGraph } from "@/lib/api";
import { layoutGraph } from "@/lib/layout";
import WorkflowNode, { type WorkflowNodeData } from "./WorkflowNode";

const nodeTypes = { workflow: WorkflowNode };

/** Build the visited node-set and taken edge ids for the most recent call. */
function takenPath(graph: WorkflowGraph, call: CallRecord | null) {
  const nodes = new Set<string>();
  const edges = new Set<string>();
  if (!call) return { nodes, edges };

  // Walk from entry following edges whose `on` matches the call outcome.
  // We also always mark the entry node and any current_node_id as visited.
  if (graph.entry) nodes.add(graph.entry);
  if (call.current_node_id) nodes.add(call.current_node_id);

  const bySource = new Map<string, typeof graph.edges>();
  for (const e of graph.edges) {
    if (!bySource.has(e.source)) bySource.set(e.source, []);
    bySource.get(e.source)!.push(e);
  }

  const outcome = call.outcome;
  // Greedy walk: from each visited node, take an edge matching the outcome.
  let cursor: string | null = graph.entry || graph.nodes[0]?.id || null;
  const guard = new Set<string>();
  while (cursor && !guard.has(cursor)) {
    guard.add(cursor);
    nodes.add(cursor);
    const outs = bySource.get(cursor) ?? [];
    // Prefer the edge whose outcome matches the call outcome.
    let next = outcome ? outs.find((e) => e.on === outcome) : undefined;
    // If exactly one outgoing edge, follow it as the deterministic path.
    if (!next && outs.length === 1) next = outs[0];
    if (!next) break;
    edges.add(`${next.source}-${next.target}-${next.on}`);
    cursor = next.target;
  }
  return { nodes, edges };
}

export default function WorkflowVisualizer({
  graph,
  livePoll = true,
}: {
  graph: WorkflowGraph | null;
  livePoll?: boolean;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const latestCall = useRef<CallRecord | null>(null);

  const baseNodes = useMemo<Node[]>(() => {
    if (!graph) return [];
    const pos = layoutGraph(graph);
    return graph.nodes.map((n) => {
      const data: WorkflowNodeData = {
        label: n.label,
        kind: n.type,
        tool: n.tool,
        agentId: n.agent_id,
        outcomes: n.outcomes ?? [],
        active: false,
      };
      return {
        id: n.id,
        type: "workflow",
        position: { x: pos[n.id]?.x ?? 0, y: pos[n.id]?.y ?? 0 },
        data: data as unknown as Record<string, unknown>,
      };
    });
  }, [graph]);

  const baseEdges = useMemo<Edge[]>(() => {
    if (!graph) return [];
    return graph.edges.map((e) => ({
      id: `${e.source}-${e.target}-${e.on}`,
      source: e.source,
      target: e.target,
      label: e.on,
      labelBgPadding: [4, 2] as [number, number],
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#2a2d36" },
    }));
  }, [graph]);

  // Apply the highlight overlay onto base nodes/edges.
  const applyHighlight = useCallback(
    (call: CallRecord | null) => {
      if (!graph) return;
      const { nodes: vNodes, edges: vEdges } = takenPath(graph, call);
      setNodes(
        baseNodes.map((n) => ({
          ...n,
          data: { ...(n.data as object), active: vNodes.has(n.id) },
        })),
      );
      setEdges(
        baseEdges.map((e) => {
          const taken = vEdges.has(e.id);
          return {
            ...e,
            animated: taken,
            style: { stroke: taken ? "#c8f135" : "#2a2d36", strokeWidth: taken ? 2.5 : 1 },
            markerEnd: { type: MarkerType.ArrowClosed, color: taken ? "#c8f135" : "#2a2d36" },
          };
        }),
      );
    },
    [graph, baseNodes, baseEdges, setNodes, setEdges],
  );

  // Re-render when the graph changes.
  useEffect(() => {
    applyHighlight(latestCall.current);
  }, [applyHighlight]);

  // Poll calls for live path highlighting.
  useEffect(() => {
    if (!graph || !livePoll) return;
    let alive = true;
    const tick = async () => {
      try {
        const calls = await listCalls();
        if (!alive) return;
        // Most recent call for this workflow (fall back to most recent overall).
        const sorted = [...calls].sort(
          (a, b) => +new Date(b.created_at) - +new Date(a.created_at),
        );
        const forWf =
          sorted.find((c) => c.workflow_id && c.workflow_id === graph.id) ?? sorted[0] ?? null;
        latestCall.current = forWf;
        applyHighlight(forWf);
      } catch {
        /* ignore poll errors */
      }
    };
    tick();
    const t = setInterval(tick, 4000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [graph, livePoll, applyHighlight]);

  if (!graph) {
    return (
      <div className="flow-wrap" style={{ display: "grid", placeItems: "center" }}>
        <span className="muted">Select a template or generate a workflow to visualize it.</span>
      </div>
    );
  }

  return (
    <div className="flow-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Background color="#23252d" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
