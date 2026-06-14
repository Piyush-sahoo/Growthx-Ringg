import type { WorkflowGraph } from "@/lib/api";

export interface Positioned {
  id: string;
  x: number;
  y: number;
}

const X_GAP = 320;
const Y_GAP = 124;

/**
 * Layered left-to-right layout: BFS depth from the entry node maps to columns
 * (x), and siblings within a column stack vertically (y). This keeps wide
 * branching (e.g. a 6-way call) readable as a tidy vertical column per level.
 * Nodes unreachable from entry are appended in a trailing column.
 */
export function layoutGraph(graph: WorkflowGraph): Record<string, Positioned> {
  const adj = new Map<string, string[]>();
  for (const n of graph.nodes) adj.set(n.id, []);
  for (const e of graph.edges) {
    if (adj.has(e.source)) adj.get(e.source)!.push(e.target);
  }

  const depth = new Map<string, number>();
  const queue: string[] = [];
  const entry = graph.entry && adj.has(graph.entry) ? graph.entry : graph.nodes[0]?.id;
  if (entry) {
    depth.set(entry, 0);
    queue.push(entry);
  }
  while (queue.length) {
    const cur = queue.shift()!;
    const d = depth.get(cur)!;
    for (const next of adj.get(cur) ?? []) {
      if (!depth.has(next)) {
        depth.set(next, d + 1);
        queue.push(next);
      }
    }
  }

  // Unreached nodes go on a level after the deepest reached one.
  let maxDepth = 0;
  depth.forEach((d) => {
    maxDepth = Math.max(maxDepth, d);
  });
  for (const n of graph.nodes) {
    if (!depth.has(n.id)) depth.set(n.id, maxDepth + 1);
  }

  // Group by depth.
  const levels = new Map<number, string[]>();
  for (const n of graph.nodes) {
    const d = depth.get(n.id)!;
    if (!levels.has(d)) levels.set(d, []);
    levels.get(d)!.push(n.id);
  }

  const result: Record<string, Positioned> = {};
  for (const [d, ids] of Array.from(levels.entries()).sort((a, b) => a[0] - b[0])) {
    const total = ids.length;
    ids.forEach((id, i) => {
      const y = (i - (total - 1) / 2) * Y_GAP;
      result[id] = { id, x: d * X_GAP, y };
    });
  }
  return result;
}
