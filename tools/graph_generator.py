"""Generate a self-contained interactive HTML graph from a full analysis JSON."""

import json
import re
import sys
from pathlib import Path


def strip_bold(text: str) -> str:
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text or "")


# ── Visual config ──────────────────────────────────────────────────────────────

NODE_TYPES = {
    # Contexte
    "why_read":            {"color": "#80cbc4", "size": 15, "icon": "→", "label": "Why Read",            "group": "Contexte"},
    "context":             {"color": "#4682b4", "size": 16, "icon": "i", "label": "Context",              "group": "Contexte"},
    "important_fact":      {"color": "#4db6ac", "size": 16, "icon": "✓", "label": "Important Fact",      "group": "Contexte"},
    # Alertes
    "watch_out":           {"color": "#ff8c00", "size": 16, "icon": "⚠", "label": "Watch Out",           "group": "Alertes"},
    # Logique
    "premisse":            {"color": "#81c784", "size": 15, "icon": "P", "label": "Premisse",             "group": "Logique"},
    "implicit_assumption": {"color": "#c9ae5d", "size": 15, "icon": "?", "label": "Implicit Assumption", "group": "Logique"},
    "blind_spot":          {"color": "#a1887f", "size": 15, "icon": "◉", "label": "Blind Spot",          "group": "Logique"},
    "logical_reasoning":   {"color": "#9575cd", "size": 15, "icon": "L", "label": "Logical Reasoning",   "group": "Logique"},
    # Thèse
    "main_claim":          {"color": "#d4aa00", "size": 26, "icon": "★", "label": "Main Claim",          "group": "Thèse"},
    # Fond
    "observation":         {"color": "#4fc3f7", "size": 22, "icon": "◎", "label": "Observation",         "group": "Fond"},
    "steel_man":           {"color": "#78909c", "size": 16, "icon": "⚔", "label": "Steel Man",           "group": "Fond"},
    # Forme
    "emotional_register":  {"color": "#f48fb1", "size": 18, "icon": "♥", "label": "Emotional Register",  "group": "Forme"},
    "cui_bono":            {"color": "#ffb74d", "size": 18, "icon": "✦", "label": "Cui Bono",            "group": "Forme"},
    # Local
    "claim":               {"color": "#66bb6a", "size": 18, "icon": "F", "label": "Claim / Fact",        "group": "Local"},
    "bias":                {"color": "#ef5350", "size": 18, "icon": "!", "label": "Bias / Rhetoric",      "group": "Local"},
    "focus":               {"color": "#ab47bc", "size": 20, "icon": "◈", "label": "Focus",               "group": "Local"},
    # Synthèse
    "synthesis":           {"color": "#ffd54f", "size": 22, "icon": "◆", "label": "Synthesis Point",     "group": "Synthèse"},
}

EDGE_TYPES = {
    "seeds":         {"color": "rgba(180,180,180,0.45)", "dash": [7, 4],  "width": 1.5, "label": "seeds"},
    "proves":        {"color": "rgba(255,255,255,0.65)", "dash": [],       "width": 2.0, "label": "proves"},
    "synthesis_ref": {"color": "rgba(255,213,79,0.55)",  "dash": [3, 3],  "width": 1.5, "label": "synthesis ref"},
    "structural":    {"color": "rgba(255,255,255,0.12)", "dash": [],       "width": 1.0, "label": "structural"},
}

# Initial x positions by group (left = upstream, right = downstream)
GROUP_X = {
    "Contexte":  -700,
    "Alertes":   -500,
    "Logique":   -300,
    "Thèse":        0,
    "Fond":       220,
    "Forme":      420,
    "Local":      620,
    "Synthèse":   820,
}


# ── Graph extraction ───────────────────────────────────────────────────────────

def build_graph(data: dict) -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()

    def add_node(nid: str, ntype: str, label: str, detail: str = "", extra: dict | None = None):
        if nid in node_ids:
            return
        node_ids.add(nid)
        cfg = NODE_TYPES.get(ntype, {"color": "#888", "size": 15, "group": "Other"})
        nodes.append({
            "id": nid,
            "type": ntype,
            "label": strip_bold(label),
            "detail": strip_bold(detail),
            "color": cfg["color"],
            "size": cfg["size"],
            "icon": cfg.get("icon", "?"),
            "group": cfg.get("group", "Other"),
            **(extra or {}),
        })

    def add_edge(src: str, tgt: str, etype: str, label: str = "", strength: float = 0.5):
        if src not in node_ids or tgt not in node_ids:
            return
        if src == tgt:
            return
        edges.append({"source": src, "target": tgt, "type": etype, "label": label, "strength": strength})

    # ── Context nodes ─────────────────────────────────────────────────────────

    why_read = data.get("interest", {}).get("why_read", "")
    if why_read:
        add_node("why_read", "why_read", why_read, why_read)

    # ── Seed source nodes ──────────────────────────────────────────────────────

    for i, item in enumerate(data.get("watch_out", {}).get("items", [])):
        text = item.get("text", str(item))
        add_node(f"watch_out_{i}", "watch_out", text, text)

    ctx = data.get("context", {})
    for i, item in enumerate(ctx.get("contexts", [])):
        text = item.get("text", str(item))
        add_node(f"context_{i}", "context", text, text)

    for i, item in enumerate(ctx.get("important_facts", [])):
        text = item.get("text", str(item))
        add_node(f"important_fact_{i}", "important_fact", text, text)

    fond = data.get("analysis", {}).get("fond", {})

    for i, p in enumerate(fond.get("premisses", [])):
        add_node(f"premisse_{i}", "premisse", p.get("statement", ""), p.get("quality", ""))

    for i, ia in enumerate(fond.get("implicit_assumptions", [])):
        text = ia.get("statement", ia.get("text", ""))
        add_node(f"implicit_assumption_{i}", "implicit_assumption", text, ia.get("impact", ""))

    for i, bs in enumerate(fond.get("blind_spots", [])):
        text = bs.get("topic", bs.get("text", ""))
        add_node(f"blind_spot_{i}", "blind_spot", text, bs.get("significance", ""))

    for i, lr in enumerate(fond.get("logical_reasoning", [])):
        detail = f"{lr.get('problem_type', '')} — {lr.get('diagnosis', '')}"
        add_node(f"logical_reasoning_{i}", "logical_reasoning", lr.get("step", ""), detail)

    # ── Core ──────────────────────────────────────────────────────────────────

    main_claim = fond.get("main_claim", "")
    add_node("main_claim", "main_claim", main_claim, main_claim)

    for i in range(len(fond.get("premisses", []))):
        add_edge(f"premisse_{i}", "main_claim", "structural")
    for i in range(len(fond.get("implicit_assumptions", []))):
        add_edge(f"implicit_assumption_{i}", "main_claim", "structural")
    for i in range(len(fond.get("blind_spots", []))):
        add_edge(f"blind_spot_{i}", "main_claim", "structural")
    for i in range(len(fond.get("logical_reasoning", []))):
        add_edge(f"logical_reasoning_{i}", "main_claim", "structural")

    # ── Analysis nodes ────────────────────────────────────────────────────────

    def resolve_seed(seeds: dict) -> str:
        src = seeds.get("source", "")
        idx = seeds.get("index", 0)
        return f"{src}_{idx}"

    for obs in fond.get("observations", []):
        nid = obs.get("id") or f"obs_{fond['observations'].index(obs)}"
        label = f"{obs.get('aspect', '')}: {obs.get('summary', '')}"
        add_node(nid, "observation", label, obs.get("summary", ""))
        seeds = obs.get("seeds", {})
        if seeds:
            add_edge(resolve_seed(seeds), nid, "seeds",
                     seeds.get("nature", ""), seeds.get("strength") or 0.5)

    forme = data.get("analysis", {}).get("forme", {})

    for er in forme.get("emotional_register", []):
        nid = er.get("id") or f"er_{forme['emotional_register'].index(er)}"
        detail = f"{er.get('how', '')} — effect: {er.get('effect', '')}"
        add_node(nid, "emotional_register", er.get("emotion", ""), detail)
        seeds = er.get("seeds", {})
        if seeds:
            add_edge(resolve_seed(seeds), nid, "seeds",
                     seeds.get("nature", ""), seeds.get("strength") or 0.5)

    for cb in forme.get("cui_bono", []):
        nid = cb.get("id") or f"cb_{forme['cui_bono'].index(cb)}"
        add_node(nid, "cui_bono", cb.get("beneficiary", ""), cb.get("explanation", ""))
        seeds = cb.get("seeds", {})
        if seeds:
            add_edge(resolve_seed(seeds), nid, "seeds",
                     seeds.get("nature", ""), seeds.get("strength") or 0.5)

    for i, sm in enumerate(fond.get("steel_man", [])):
        nid = f"steel_man_{i}"
        detail = f"Alt conclusion: {sm.get('alternative_conclusion', '')}"
        add_node(nid, "steel_man", sm.get("counterargument", ""), detail)
        seeds = sm.get("seeds", {})
        if seeds:
            add_edge(resolve_seed(seeds), nid, "seeds",
                     seeds.get("nature", ""), seeds.get("strength") or 0.5)

    # ── Evidence nodes ────────────────────────────────────────────────────────

    obs_by_aspect: dict[str, str] = {}
    for obs in fond.get("observations", []):
        nid = obs.get("id") or f"obs_{fond['observations'].index(obs)}"
        obs_by_aspect[obs.get("aspect", "").strip().lower()] = nid

    er_by_emotion: dict[str, str] = {}
    for er in forme.get("emotional_register", []):
        nid = er.get("id") or f"er_{forme['emotional_register'].index(er)}"
        er_by_emotion[er.get("emotion", "").strip().lower()] = nid

    cb_by_beneficiary: dict[str, str] = {}
    for cb in forme.get("cui_bono", []):
        nid = cb.get("id") or f"cb_{forme['cui_bono'].index(cb)}"
        cb_by_beneficiary[cb.get("beneficiary", "").strip().lower()] = nid

    def resolve_proves(proves: dict) -> str | None:
        ptype = proves.get("type", "")
        plabel = proves.get("label", "").strip().lower()
        if ptype == "observation":
            return obs_by_aspect.get(plabel)
        if ptype == "emotional_register":
            return er_by_emotion.get(plabel)
        if ptype == "cui_bono":
            return cb_by_beneficiary.get(plabel)
        return None

    fvo = data.get("annotations", {}).get("facts_vs_opinions", {})
    for claim in fvo.get("claims_and_sources", []):
        nid = claim.get("id") or f"claim_{fvo['claims_and_sources'].index(claim)}"
        confidence = claim.get("confidence")
        conf_label = claim.get("confidence_label", "")
        detail = f"{claim.get('explanation', '')}\nConfidence: {confidence}% ({conf_label})"
        add_node(nid, "claim", claim.get("quote", ""), detail,
                 {"confidence": confidence, "presentation": claim.get("presentation", "")})
        proves = claim.get("proves", {})
        if proves:
            tgt = resolve_proves(proves)
            if tgt:
                add_edge(nid, tgt, "proves",
                         proves.get("nature", ""), proves.get("strength") or 0.6)

    baf = data.get("annotations", {}).get("biases_and_focus", {})
    for bias in baf.get("biases_and_rhetoric", []):
        nid = bias.get("id") or f"bias_{baf['biases_and_rhetoric'].index(bias)}"
        label = f"[{bias.get('label', '')}] {bias.get('quote', '')}"
        add_node(nid, "bias", label, bias.get("effect", ""),
                 {"item_type": bias.get("item_type", "bias"), "bias_label": bias.get("label", "")})
        proves = bias.get("proves", {})
        if proves:
            tgt = resolve_proves(proves)
            if tgt:
                add_edge(nid, tgt, "proves",
                         proves.get("nature", ""), proves.get("strength") or 0.6)

    focus = baf.get("focus", {})
    if focus:
        add_node("focus", "focus", focus.get("quote", ""), focus.get("analysis", ""))
        proves = focus.get("proves", {})
        if proves:
            tgt = resolve_proves(proves)
            if tgt:
                add_edge("focus", tgt, "proves",
                         proves.get("nature", ""), proves.get("strength") or 0.6)

    # ── Synthesis ─────────────────────────────────────────────────────────────

    synth = data.get("synthesis", {})
    for i, sp in enumerate(synth.get("synthesis_points", [])):
        nid = f"synthesis_{i}"
        add_node(nid, "synthesis", sp.get("text", ""), sp.get("text", ""))
        for ref in sp.get("references", []):
            add_edge(nid, ref, "synthesis_ref", "ref", 0.4)

    return nodes, edges


# ── HTML generation ────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0a0a0a; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; display: flex; height: 100vh; overflow: hidden; }

#sidebar { width: 300px; min-width: 300px; background: #111; border-right: 1px solid #222; display: flex; flex-direction: column; overflow: hidden; }
#sidebar-header { padding: 16px 18px 12px; border-bottom: 1px solid #222; }
#sidebar-header h1 { font-size: 14px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #d4aa00; }
#sidebar-header p { font-size: 12px; color: #666; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

#sidebar-body { flex: 1; overflow-y: auto; padding: 14px 18px; }
#sidebar-body::-webkit-scrollbar { width: 4px; }
#sidebar-body::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.section-title { font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #555; margin: 16px 0 8px; }

#search {
  width: 100%; padding: 5px 10px; margin-bottom: 4px;
  background: #181818; border: 1px solid #333; border-radius: 4px;
  color: #e0e0e0; font-size: 12px; outline: none;
}
#search:focus { border-color: #666; }
#search::placeholder { color: #444; }

#focus-bar {
  display: none; padding: 4px 8px; background: #1a1800; border: 1px solid #d4aa00;
  border-radius: 4px; font-size: 10px; color: #d4aa00; margin-bottom: 6px;
  text-align: center; line-height: 1.4;
}

.legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; cursor: pointer; padding: 3px 4px; border-radius: 4px; }
.legend-item:hover { background: #1a1a1a; }
.legend-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 8px; color: #000; font-weight: 700; }
.legend-name { font-size: 12px; color: #aaa; }
.legend-count { margin-left: auto; font-size: 11px; color: #444; }

.edge-legend { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.edge-line { width: 28px; height: 2px; flex-shrink: 0; }

#node-detail { margin-top: 4px; }
#node-detail-empty { font-size: 12px; color: #444; font-style: italic; }
#node-detail-content { display: none; }
#node-detail-type { font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px; }
#node-detail-label { font-size: 13px; color: #f0f0f0; line-height: 1.5; margin-bottom: 8px; }
#node-detail-body { font-size: 12px; color: #888; line-height: 1.6; }
#node-detail-connections { margin-top: 10px; }
.conn-item { font-size: 11px; color: #666; padding: 4px 0; border-top: 1px solid #1a1a1a; line-height: 1.4; }
.conn-item span { color: #aaa; }
.clickable { cursor: pointer; }
.clickable:hover { background: #181818; padding-left: 4px; border-radius: 3px; }

#controls { padding: 12px 18px; border-top: 1px solid #222; display: flex; gap: 6px; flex-wrap: wrap; }
.ctrl-btn { padding: 4px 9px; border: 1px solid #333; border-radius: 4px; background: #1a1a1a; color: #888; cursor: pointer; font-size: 11px; }
.ctrl-btn:hover { border-color: #555; color: #ccc; }

#canvas-wrap { flex: 1; position: relative; overflow: hidden; }
canvas { display: block; width: 100%; height: 100%; cursor: grab; }
canvas.dragging { cursor: grabbing; }

#tooltip { position: absolute; pointer-events: none; background: rgba(10,10,10,0.95); border: 1px solid #444; border-radius: 6px; padding: 10px 14px; font-size: 12px; color: #e0e0e0; max-width: 380px; max-height: 260px; overflow-y: auto; line-height: 1.6; display: none; z-index: 10; }
#tooltip .tip-type { font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 5px; }
#tooltip .tip-label { color: #f0f0f0; font-weight: 600; margin-bottom: 6px; }
#tooltip .tip-detail { color: #888; font-size: 11px; }
#tooltip .tip-note { font-size: 11px; margin-top: 6px; }
#stats { font-size: 11px; color: #333; margin-top: 4px; }
"""

# JS logic as a raw string so no Python escaping needed in JS template literals / regex
_JS_LOGIC = r"""
// ── Helpers ────────────────────────────────────────────────────────────────────
function brightenAlpha(color, factor) {
  const m = color.match(/([\d.]+)\)$/);
  if (!m) return color;
  const a = Math.min(1, parseFloat(m[1]) * factor);
  return color.replace(/([\d.]+)\)$/, a.toFixed(2) + ')');
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r); ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r); ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r); ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r); ctx.closePath();
}

// ── State ──────────────────────────────────────────────────────────────────────
let nodes, edges;
let transform = {x: 0, y: 0, scale: 1};
let dragging = null;
let hovered = null, hoveredEdge = null, detailNode = null;
let panning = false, panStart = {x:0,y:0}, panOrigin = {x:0,y:0};
let simRunning = true, alpha = 1.0;
let selectedNodes = new Set();
let focusNode = null;
let searchQuery = '';
let layoutMode = 'force';
let pinned = false;
let saveTimeout = null;

// ── Simulation params ──────────────────────────────────────────────────────────
const REPULSION = 15000;
const SPRING_K = 0.025;
const SPRING_REST = 200;
const CENTER_GRAVITY = 0.006;
const DAMPING = 0.86;
const BASE_GROUP_GRAVITY = 0.012;
const PIN_GRAVITY_FACTOR = 0.25;
const DAG_X_GRAVITY = 0.35;

// ── Init ───────────────────────────────────────────────────────────────────────
function init() {
  const nodeMap = {};
  nodes = GRAPH_DATA.nodes.map((n, i) => {
    const gx = GROUP_X[n.group] || 0;
    const node = {
      ...n,
      x: gx + (Math.random() - 0.5) * 120,
      y: (i % 8 - 4) * 80 + (Math.random() - 0.5) * 60,
      vx: 0, vy: 0,
      mass: n.size / 15,
    };
    nodeMap[n.id] = node;
    return node;
  });

  edges = GRAPH_DATA.edges.map(e => ({
    ...e,
    source: nodeMap[e.source],
    target: nodeMap[e.target],
  })).filter(e => e.source && e.target);

  // B: Compute gaps (analysis nodes with no incoming proves) and orphans (source nodes never seeded)
  const provedSet = new Set(edges.filter(e => e.type === 'proves').map(e => e.target));
  const seededSet = new Set(edges.filter(e => e.type === 'seeds').map(e => e.source));
  const analysisTypes = new Set(['observation', 'emotional_register', 'cui_bono']);
  const sourceTypes = new Set(['watch_out', 'context', 'important_fact', 'premisse', 'implicit_assumption', 'blind_spot', 'logical_reasoning']);
  nodes.forEach(n => {
    n.hasGap = analysisTypes.has(n.type) && !provedSet.has(n);
    n.isOrphan = sourceTypes.has(n.type) && !seededSet.has(n);
  });

  // H: Restore saved layout if available; soft settle
  if (loadLayout()) alpha = 0.25;

  buildLegend();
  setupCanvas();
  setupInteractions();
  loop();
  updateStats();
}

// ── Simulation ─────────────────────────────────────────────────────────────────
function tick() {
  if (alpha < 0.002) return;
  alpha *= 0.996;
  const gGrav = pinned ? PIN_GRAVITY_FACTOR : BASE_GROUP_GRAVITY;

  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const b = nodes[j];
      const dx = a.x - b.x, dy = a.y - b.y;
      const dist2 = dx*dx + dy*dy || 1;
      const dist = Math.sqrt(dist2);
      const force = REPULSION * alpha / dist2;
      const fx = dx/dist * force, fy = dy/dist * force;
      a.vx += fx / a.mass; a.vy += fy / a.mass;
      b.vx -= fx / b.mass; b.vy -= fy / b.mass;
    }
  }

  edges.forEach(e => {
    if (!e.source || !e.target) return;
    const dx = e.target.x - e.source.x, dy = e.target.y - e.source.y;
    const dist = Math.sqrt(dx*dx + dy*dy) || 1;
    const stretch = (dist - SPRING_REST) * SPRING_K * e.strength * alpha;
    const fx = dx/dist * stretch, fy = dy/dist * stretch;
    e.source.vx += fx; e.source.vy += fy;
    e.target.vx -= fx; e.target.vy -= fy;
  });

  nodes.forEach(n => {
    if (n === dragging) return;
    n.vx += (0 - n.x) * CENTER_GRAVITY * alpha;
    n.vy += (0 - n.y) * CENTER_GRAVITY * alpha;
    const gx = GROUP_X[n.group] || 0;
    if (layoutMode === 'dag') {
      n.vx += (gx - n.x) * DAG_X_GRAVITY;
    } else {
      n.vx += (gx - n.x) * gGrav * alpha * 0.3;
    }
    n.vx *= DAMPING; n.vy *= DAMPING;
    n.x += n.vx; n.y += n.vy;
  });
}

// ── Canvas ─────────────────────────────────────────────────────────────────────
const canvas = document.getElementById('graph');
const ctx = canvas.getContext('2d');

function setupCanvas() { resize(); window.addEventListener('resize', resize); }
function resize() {
  const wrap = document.getElementById('canvas-wrap');
  canvas.width = wrap.clientWidth;
  canvas.height = wrap.clientHeight;
}
function loop() { if (simRunning) tick(); render(); requestAnimationFrame(loop); }
function worldToScreen(x, y) {
  return [canvas.width/2 + transform.x + x*transform.scale, canvas.height/2 + transform.y + y*transform.scale];
}
function screenToWorld(sx, sy) {
  return [(sx - canvas.width/2 - transform.x) / transform.scale, (sy - canvas.height/2 - transform.y) / transform.scale];
}

// ── Visibility state ───────────────────────────────────────────────────────────
function getVisState() {
  if (focusNode) {
    const nb = new Set([focusNode]);
    edges.forEach(e => {
      if (e.source === focusNode) nb.add(e.target);
      if (e.target === focusNode) nb.add(e.source);
    });
    return {mode: 'focus', nodes: nb, edges: new Set(edges.filter(e => nb.has(e.source) && nb.has(e.target)))};
  }
  if (searchQuery) {
    const q = searchQuery;
    const m = new Set(nodes.filter(n => n.label.toLowerCase().includes(q) || (n.detail||'').toLowerCase().includes(q)));
    return {mode: 'search', nodes: m, edges: new Set()};
  }
  if (selectedNodes.size > 0) {
    return {mode: 'selection', nodes: selectedNodes, edges: new Set(edges.filter(e => selectedNodes.has(e.source) && selectedNodes.has(e.target)))};
  }
  return {mode: 'all', nodes: new Set(nodes), edges: new Set(edges)};
}

// ── Render ─────────────────────────────────────────────────────────────────────
function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const vis = getVisState();
  const allEdges = new Set(edges);

  // Ghost edges (very dim) when filtered
  if (vis.mode !== 'all') {
    allEdges.forEach(e => {
      if (vis.edges.has(e) || !e.source || !e.target) return;
      const [sx,sy] = worldToScreen(e.source.x, e.source.y);
      const [tx,ty] = worldToScreen(e.target.x, e.target.y);
      ctx.save(); ctx.globalAlpha = 0.04;
      ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(tx,ty);
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke();
      ctx.restore();
    });
  }

  // Visible edges
  vis.edges.forEach(e => {
    if (!e.source || !e.target) return;
    const highlight = vis.mode === 'focus' && (e.source === focusNode || e.target === focusNode);
    drawEdge(e, highlight);
  });

  // Nodes
  nodes.forEach(n => {
    let opacity = 1;
    if (vis.mode === 'focus') opacity = vis.nodes.has(n) ? 1 : 0.08;
    else if (vis.mode === 'search') opacity = vis.nodes.has(n) ? 1 : 0.12;
    else if (vis.mode === 'selection') opacity = selectedNodes.has(n) ? 1 : 0.18;
    drawNode(n, opacity);
  });

  // A: Edge hover label
  if (hoveredEdge) {
    const vis2 = getVisState();
    if (vis2.edges.has(hoveredEdge)) drawEdgeLabel(hoveredEdge);
  }
}

// A: Edge strength drives line width
function drawEdge(e, highlight) {
  const cfg = EDGE_TYPES[e.type] || EDGE_TYPES.structural;
  const [sx,sy] = worldToScreen(e.source.x, e.source.y);
  const [tx,ty] = worldToScreen(e.target.x, e.target.y);
  const strength = e.strength != null ? e.strength : 0.5;
  const lw = cfg.width * (0.4 + strength * 1.6) * (highlight ? 1.8 : 1);
  ctx.save();
  ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(tx,ty);
  ctx.strokeStyle = highlight ? brightenAlpha(cfg.color, 2.5) : cfg.color;
  ctx.lineWidth = lw;
  if (cfg.dash && cfg.dash.length) ctx.setLineDash(cfg.dash); else ctx.setLineDash([]);
  ctx.stroke(); ctx.setLineDash([]);
  drawArrow(sx,sy,tx,ty, e.target.size*transform.scale, highlight ? brightenAlpha(cfg.color, 2.5) : cfg.color, highlight);
  ctx.restore();
}

function drawArrow(sx, sy, tx, ty, targetR, color, bold) {
  const dx = tx-sx, dy = ty-sy, dist = Math.sqrt(dx*dx+dy*dy);
  if (dist < 1) return;
  const ux=dx/dist, uy=dy/dist;
  const ax=tx-ux*(targetR+3), ay=ty-uy*(targetR+3);
  const len = bold ? 11 : 8, ang = Math.PI/7;
  ctx.beginPath();
  ctx.moveTo(ax, ay);
  ctx.lineTo(ax-len*(ux*Math.cos(ang)-uy*Math.sin(ang)), ay-len*(uy*Math.cos(ang)+ux*Math.sin(ang)));
  ctx.lineTo(ax-len*(ux*Math.cos(ang)+uy*Math.sin(ang)), ay-len*(uy*Math.cos(ang)-ux*Math.sin(ang)));
  ctx.closePath(); ctx.fillStyle=color; ctx.setLineDash([]); ctx.fill();
}

// B: Gap/orphan rings drawn on analysis nodes with no proof
function drawNode(n, opacity) {
  const [sx,sy] = worldToScreen(n.x, n.y);
  const r = n.size * transform.scale;
  if (r < 1) return;
  const isSelected = selectedNodes.has(n), isDetail = n===detailNode;
  const isFocus = n===focusNode, isHovered = n===hovered;

  ctx.save(); ctx.globalAlpha = opacity;

  if (n.hasGap) {
    ctx.beginPath(); ctx.arc(sx,sy, r+5*transform.scale, 0, Math.PI*2);
    ctx.strokeStyle='#ff4444'; ctx.lineWidth=1.5; ctx.setLineDash([4,3]); ctx.stroke(); ctx.setLineDash([]);
  }
  if (n.isOrphan) {
    ctx.beginPath(); ctx.arc(sx,sy, r+4*transform.scale, 0, Math.PI*2);
    ctx.strokeStyle='#ff8800'; ctx.lineWidth=1.5; ctx.setLineDash([2,4]); ctx.stroke(); ctx.setLineDash([]);
  }

  if (isSelected||isHovered||isDetail||isFocus) {
    ctx.beginPath(); ctx.arc(sx,sy, r+8*transform.scale, 0, Math.PI*2);
    ctx.fillStyle = n.color + (isFocus?'55':isSelected?'40':'20'); ctx.fill();
  }

  ctx.beginPath(); ctx.arc(sx,sy,r,0,Math.PI*2); ctx.fillStyle=n.color; ctx.fill();

  if (isFocus) {
    ctx.strokeStyle='#fff'; ctx.lineWidth=3; ctx.setLineDash([]); ctx.stroke();
  } else if (isSelected) {
    ctx.strokeStyle='#fff'; ctx.lineWidth=2.5; ctx.setLineDash([]); ctx.stroke();
  } else if (isDetail) {
    ctx.strokeStyle='rgba(255,255,255,0.5)'; ctx.lineWidth=1.5; ctx.setLineDash([4,3]); ctx.stroke(); ctx.setLineDash([]);
  }

  if (r > 8) {
    ctx.fillStyle='rgba(0,0,0,0.75)';
    ctx.font=`bold ${Math.floor(r*0.85)}px sans-serif`;
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(n.icon, sx, sy);
  }

  if (transform.scale > 0.45 && r > 6) {
    const fs = Math.max(9, Math.min(13, 11*transform.scale));
    ctx.font=`${fs}px sans-serif`;
    ctx.fillStyle=(isSelected||isFocus)?'#fff':'rgba(220,220,220,0.7)';
    ctx.textAlign='center'; ctx.textBaseline='top';
    const lbl = n.label.length > 32 ? n.label.slice(0,32)+'…' : n.label;
    ctx.fillText(lbl, sx, sy+r+4*transform.scale);
  }
  ctx.restore();
}

// A: Edge hover label showing type, nature, strength
function drawEdgeLabel(e) {
  const [sx,sy] = worldToScreen(e.source.x, e.source.y);
  const [tx,ty] = worldToScreen(e.target.x, e.target.y);
  const mx=(sx+tx)/2, my=(sy+ty)/2;
  const cfg = EDGE_TYPES[e.type] || {};
  const parts = [];
  if (cfg.label) parts.push(cfg.label);
  if (e.label) parts.push(e.label);
  if (e.strength != null) parts.push(`str:${(e.strength*100).toFixed(0)}%`);
  const text = parts.join(' · ');
  if (!text) return;
  ctx.save();
  ctx.font='11px sans-serif';
  const tw = ctx.measureText(text).width + 14, th = 18;
  ctx.fillStyle='rgba(10,10,10,0.9)';
  roundRect(ctx, mx-tw/2, my-th/2, tw, th, 4); ctx.fill();
  ctx.fillStyle='#ccc'; ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(text, mx, my);
  ctx.restore();
}

// ── Interactions ───────────────────────────────────────────────────────────────
function setupInteractions() {
  canvas.addEventListener('mousedown', onMouseDown);
  canvas.addEventListener('mousemove', onMouseMove);
  canvas.addEventListener('mouseup', onMouseUp);
  canvas.addEventListener('wheel', onWheel, {passive: false});
  canvas.addEventListener('dblclick', onDblClick);

  document.getElementById('btn-reset').addEventListener('click', () => { transform = {x:0,y:0,scale:1}; });
  document.getElementById('btn-pause').addEventListener('click', () => {
    simRunning = !simRunning;
    document.getElementById('btn-pause').textContent = simRunning ? 'Pause' : 'Resume';
  });
  document.getElementById('btn-reheat').addEventListener('click', () => {
    alpha=1.0; simRunning=true; document.getElementById('btn-pause').textContent='Pause';
  });
  document.getElementById('btn-clear').addEventListener('click', clearAll);

  // F: Hierarchical layout toggle
  document.getElementById('btn-layout').addEventListener('click', () => {
    layoutMode = layoutMode === 'force' ? 'dag' : 'force';
    document.getElementById('btn-layout').textContent = layoutMode==='dag' ? 'Force layout' : 'DAG layout';
    if (layoutMode === 'dag') nodes.forEach(n => { n.x = GROUP_X[n.group]||0; n.vx=0; });
    alpha=1.0; simRunning=true; document.getElementById('btn-pause').textContent='Pause';
  });

  // G: Pin nodes to group columns
  document.getElementById('btn-pin').addEventListener('click', () => {
    pinned = !pinned;
    document.getElementById('btn-pin').textContent = pinned ? 'Unpin groups' : 'Pin groups';
    alpha=1.0; simRunning=true;
  });

  // I: Export PNG
  document.getElementById('btn-export').addEventListener('click', exportPNG);

  // D: Search
  document.getElementById('search').addEventListener('input', e => {
    searchQuery = e.target.value.toLowerCase().trim();
    updateStats();
  });
}

function clearAll() {
  selectedNodes.clear(); focusNode=null;
  document.getElementById('search').value=''; searchQuery='';
  document.getElementById('focus-bar').style.display='none';
  document.querySelectorAll('.legend-item[data-type]').forEach(el => {
    el.style.opacity='1'; el.style.background=''; el.style.borderRadius='';
  });
  updateStats();
}

// A: Edge hover detection
function edgeAt(sx, sy) {
  const [wx,wy] = screenToWorld(sx,sy);
  let best=null, bestDist=10/transform.scale;
  edges.forEach(e => {
    if (!e.source||!e.target) return;
    const dx=e.target.x-e.source.x, dy=e.target.y-e.source.y;
    const len2=dx*dx+dy*dy||1;
    const t=Math.max(0,Math.min(1,((wx-e.source.x)*dx+(wy-e.source.y)*dy)/len2));
    const px=e.source.x+t*dx-wx, py=e.source.y+t*dy-wy;
    const d=Math.sqrt(px*px+py*py);
    if (d<bestDist) { bestDist=d; best=e; }
  });
  return best;
}

function nodeAt(sx, sy) {
  const [wx,wy] = screenToWorld(sx,sy);
  let best=null, bestDist=Infinity;
  nodes.forEach(n => {
    const d=Math.sqrt((n.x-wx)**2+(n.y-wy)**2);
    if (d<n.size*1.5 && d<bestDist) { best=n; bestDist=d; }
  });
  return best;
}

function onMouseDown(e) {
  const n = nodeAt(e.offsetX, e.offsetY);
  if (n) {
    dragging=n; canvas.classList.add('dragging');
    if (selectedNodes.has(n)) selectedNodes.delete(n); else selectedNodes.add(n);
    updateStats(); updateLegendHighlight(); showDetail(n);
  } else {
    panning=true; panStart={x:e.offsetX,y:e.offsetY}; panOrigin={x:transform.x,y:transform.y};
    canvas.classList.add('dragging');
  }
}

function onMouseMove(e) {
  if (dragging) {
    const [wx,wy]=screenToWorld(e.offsetX,e.offsetY);
    dragging.x=wx; dragging.y=wy; dragging.vx=0; dragging.vy=0;
    scheduleSave(); return;
  }
  if (panning) {
    transform.x=panOrigin.x+(e.offsetX-panStart.x);
    transform.y=panOrigin.y+(e.offsetY-panStart.y); return;
  }
  const n=nodeAt(e.offsetX,e.offsetY);
  hovered=n; hoveredEdge=n?null:edgeAt(e.offsetX,e.offsetY);
  showTooltip(n,e.offsetX,e.offsetY);
}

function onMouseUp() {
  if (dragging) scheduleSave();
  dragging=null; panning=false; canvas.classList.remove('dragging');
}

function onWheel(e) {
  e.preventDefault();
  const factor=e.deltaY<0?1.12:0.89;
  const mx=e.offsetX-canvas.width/2, my=e.offsetY-canvas.height/2;
  transform.x=mx-(mx-transform.x)*factor;
  transform.y=my-(my-transform.y)*factor;
  transform.scale=Math.max(0.1,Math.min(5,transform.scale*factor));
}

// C: Focus mode — double-click a node to show only it and neighbors
function onDblClick(e) {
  const n=nodeAt(e.offsetX,e.offsetY);
  const fb=document.getElementById('focus-bar');
  if (n) {
    if (focusNode===n) {
      focusNode=null; fb.style.display='none';
    } else {
      focusNode=n;
      transform.x=-n.x*transform.scale; transform.y=-n.y*transform.scale;
      const lbl=n.label.length>35?n.label.slice(0,35)+'…':n.label;
      fb.textContent=`Focus: ${lbl} — dbl-click again to exit`;
      fb.style.display='block';
    }
  } else if (focusNode) {
    focusNode=null; fb.style.display='none';
  }
  updateStats();
}

function showTooltip(n, sx, sy) {
  const tip=document.getElementById('tooltip');
  if (!n) { tip.style.display='none'; return; }
  const cfg=NODE_TYPES[n.type]||{};
  const note=n.hasGap?`<div class="tip-note" style="color:#f88">⚠ No proof edges (gap)</div>`
            :n.isOrphan?`<div class="tip-note" style="color:#fa0">○ Not referenced as seed</div>`:'';
  const detail=n.detail && n.detail!==n.label ? `<div class="tip-detail">${n.detail}</div>` : '';
  tip.innerHTML=`<div class="tip-type" style="color:${n.color}">${cfg.label||n.type}</div>`
               +`<div class="tip-label">${n.label}</div>`
               +detail+note;
  tip.style.display='block';
  const tw=Math.min(380, tip.offsetWidth||200);
  const th=Math.min(260, tip.offsetHeight||60);
  tip.style.left=(sx+16+tw>canvas.width?sx-tw-16:sx+16)+'px';
  tip.style.top=Math.min(sy+8, canvas.height-th-8)+'px';
}

function showDetail(n) {
  detailNode=n;
  const empty=document.getElementById('node-detail-empty');
  const content=document.getElementById('node-detail-content');
  if (!n) { empty.style.display=''; content.style.display='none'; return; }
  empty.style.display='none'; content.style.display='';
  const cfg=NODE_TYPES[n.type]||{};
  document.getElementById('node-detail-type').textContent=cfg.label||n.type;
  document.getElementById('node-detail-type').style.color=n.color;
  document.getElementById('node-detail-label').textContent=n.label;
  document.getElementById('node-detail-body').textContent=n.detail||'';

  const connEl=document.getElementById('node-detail-connections');
  const outEdges=edges.filter(e=>e.source===n);
  const inEdges=edges.filter(e=>e.target===n);
  let html='';
  if (inEdges.length) {
    html+=`<div class="section-title" style="margin-top:8px">← Incoming (${inEdges.length})</div>`;
    inEdges.forEach(e => {
      const c=NODE_TYPES[e.source.type]||{};
      const nat=e.label?` · ${e.label}`:'';
      const str=e.strength!=null?` · ${(e.strength*100).toFixed(0)}%`:'';
      // E: clickable — navigateTo highlights and centers on that node
      html+=`<div class="conn-item clickable" onclick="navigateTo('${e.source.id}')">
        <span style="color:${e.source.color}">[${c.label||e.source.type}]</span> ${e.source.label.slice(0,45)}<br>
        <span style="color:#444">${e.type}${nat}${str}</span>
      </div>`;
    });
  }
  if (outEdges.length) {
    html+=`<div class="section-title" style="margin-top:8px">→ Outgoing (${outEdges.length})</div>`;
    outEdges.forEach(e => {
      const c=NODE_TYPES[e.target.type]||{};
      const nat=e.label?` · ${e.label}`:'';
      const str=e.strength!=null?` · ${(e.strength*100).toFixed(0)}%`:'';
      html+=`<div class="conn-item clickable" onclick="navigateTo('${e.target.id}')">
        <span style="color:${e.target.color}">[${c.label||e.target.type}]</span> ${e.target.label.slice(0,45)}<br>
        <span style="color:#444">${e.type}${nat}${str}</span>
      </div>`;
    });
  }
  connEl.innerHTML=html;
}

// E: Jump to a node from the detail panel connections list
function navigateTo(nodeId) {
  const n=nodes.find(nd=>nd.id===nodeId);
  if (!n) return;
  selectedNodes.add(n); showDetail(n);
  updateStats(); updateLegendHighlight();
  transform.x=-n.x*transform.scale; transform.y=-n.y*transform.scale;
}

// ── Legend ─────────────────────────────────────────────────────────────────────
function buildLegend() {
  const counts={};
  nodes.forEach(n => { counts[n.type]=(counts[n.type]||0)+1; });

  const legendEl=document.getElementById('legend-nodes');
  let lastGroup=null;
  Object.entries(NODE_TYPES).forEach(([type,cfg]) => {
    const count=counts[type]||0; if (!count) return;
    if (cfg.group!==lastGroup) {
      lastGroup=cfg.group;
      legendEl.innerHTML+=`<div class="section-title" style="margin-top:10px;margin-bottom:4px">${cfg.group}</div>`;
    }
    legendEl.innerHTML+=`<div class="legend-item" data-type="${type}" onclick="toggleType('${type}')">
      <div class="legend-dot" style="background:${cfg.color}">${cfg.icon}</div>
      <span class="legend-name">${cfg.label}</span>
      <span class="legend-count">${count}</span>
    </div>`;
  });

  const edgeEl=document.getElementById('legend-edges');
  Object.entries(EDGE_TYPES).forEach(([type,cfg]) => {
    const count=edges.filter(e=>e.type===type).length; if (!count) return;
    const bStyle=(cfg.dash&&cfg.dash.length)
      ?`border-top:2px dashed ${brightenAlpha(cfg.color,2)};`
      :`border-top:2px solid ${brightenAlpha(cfg.color,2)};`;
    edgeEl.innerHTML+=`<div class="edge-legend">
      <div class="edge-line" style="${bStyle}"></div>
      <span class="legend-name">${cfg.label} <small style="color:#444">strength=width</small></span>
      <span class="legend-count" style="margin-left:auto">${count}</span>
    </div>`;
  });

  // B: Show gap/orphan counts in legend
  const gapCount=nodes.filter(n=>n.hasGap).length;
  const orphanCount=nodes.filter(n=>n.isOrphan).length;
  if (gapCount) edgeEl.innerHTML+=`<div class="edge-legend">
    <div style="width:20px;height:14px;border:1.5px dashed #f44;border-radius:7px;flex-shrink:0"></div>
    <span class="legend-name" style="color:#f88">Gap (no proof)</span>
    <span class="legend-count" style="margin-left:auto">${gapCount}</span>
  </div>`;
  if (orphanCount) edgeEl.innerHTML+=`<div class="edge-legend">
    <div style="width:20px;height:14px;border:1.5px dashed #f80;border-radius:7px;flex-shrink:0"></div>
    <span class="legend-name" style="color:#fa0">Orphan (unused)</span>
    <span class="legend-count" style="margin-left:auto">${orphanCount}</span>
  </div>`;
}

function toggleType(type) {
  const tNodes=nodes.filter(n=>n.type===type);
  const allSel=tNodes.length>0 && tNodes.every(n=>selectedNodes.has(n));
  if (allSel) tNodes.forEach(n=>selectedNodes.delete(n)); else tNodes.forEach(n=>selectedNodes.add(n));
  updateLegendHighlight(); updateStats();
}

function updateLegendHighlight() {
  document.querySelectorAll('.legend-item[data-type]').forEach(el => {
    const tNodes=nodes.filter(n=>n.type===el.dataset.type);
    const active=tNodes.length>0 && tNodes.every(n=>selectedNodes.has(n));
    el.style.background=active?'#252525':'';
    el.style.borderRadius=active?'4px':'';
    el.style.opacity=(selectedNodes.size===0||active)?'1':'0.45';
  });
}

function updateStats() {
  const el=document.getElementById('stats');
  if (focusNode) {
    const nb=new Set([focusNode]);
    edges.forEach(e => { if(e.source===focusNode)nb.add(e.target); if(e.target===focusNode)nb.add(e.source); });
    const ec=edges.filter(e=>nb.has(e.source)&&nb.has(e.target)).length;
    el.textContent=`Focus: ${nb.size} nodes · ${ec} edges`;
  } else if (searchQuery) {
    const m=nodes.filter(n=>n.label.toLowerCase().includes(searchQuery)||(n.detail||'').toLowerCase().includes(searchQuery)).length;
    el.textContent=`Search: ${m} / ${nodes.length} nodes`;
  } else if (selectedNodes.size>0) {
    const ve=edges.filter(e=>selectedNodes.has(e.source)&&selectedNodes.has(e.target)).length;
    el.textContent=`${selectedNodes.size} / ${nodes.length} nodes · ${ve} edges`;
  } else {
    el.textContent=`${nodes.length} nodes · ${edges.length} edges`;
  }
}

// ── H: localStorage layout persistence ────────────────────────────────────────
const STORAGE_KEY = 'graph_layout_' + ARTICLE_TITLE.replace(/\s+/g, '_').slice(0, 40);
function scheduleSave() { clearTimeout(saveTimeout); saveTimeout=setTimeout(saveLayout,3000); }
function saveLayout() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nodes.map(n=>({id:n.id,x:Math.round(n.x),y:Math.round(n.y)}))));
  } catch(err) {}
}
function loadLayout() {
  try {
    const saved=localStorage.getItem(STORAGE_KEY);
    if (!saved) return false;
    const map={};
    JSON.parse(saved).forEach(item => { map[item.id]=item; });
    let found=0;
    nodes.forEach(n => { if(map[n.id]){n.x=map[n.id].x;n.y=map[n.id].y;found++;} });
    return found>0;
  } catch(err) { return false; }
}

// ── I: Export canvas as PNG ────────────────────────────────────────────────────
function exportPNG() {
  render();
  const url=canvas.toDataURL('image/png');
  const a=document.createElement('a');
  a.href=url; a.download='analysis_graph.png';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}

init();
"""


def generate_html(nodes: list[dict], edges: list[dict], title: str) -> str:
    graph_data = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)
    node_types_js = json.dumps(NODE_TYPES, ensure_ascii=False)
    edge_types_js = json.dumps(EDGE_TYPES, ensure_ascii=False)
    group_x_js = json.dumps(GROUP_X)
    title_js = json.dumps(title)

    js_data = (
        f"const GRAPH_DATA = {graph_data};\n"
        f"const NODE_TYPES = {node_types_js};\n"
        f"const EDGE_TYPES = {edge_types_js};\n"
        f"const GROUP_X = {group_x_js};\n"
        f"const ARTICLE_TITLE = {title_js};\n"
    )

    return (
        f'<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="UTF-8">\n'
        f'<title>Graph — {title}</title>\n<style>\n'
        + _CSS
        + '</style>\n</head>\n<body>\n'
        '<div id="sidebar">\n'
        '  <div id="sidebar-header">\n'
        '    <h1>Analysis Graph</h1>\n'
        f'    <p id="article-title">{title}</p>\n'
        '  </div>\n'
        '  <div id="sidebar-body">\n'
        '    <input type="text" id="search" placeholder="Search nodes…" autocomplete="off">\n'
        '    <div id="focus-bar"></div>\n'
        '    <div class="section-title">Node types</div>\n'
        '    <div id="legend-nodes"></div>\n'
        '    <div class="section-title">Edge types</div>\n'
        '    <div id="legend-edges"></div>\n'
        '    <div class="section-title">Selected node</div>\n'
        '    <div id="node-detail">\n'
        '      <div id="node-detail-empty">Click a node to inspect</div>\n'
        '      <div id="node-detail-content">\n'
        '        <div id="node-detail-type"></div>\n'
        '        <div id="node-detail-label"></div>\n'
        '        <div id="node-detail-body"></div>\n'
        '        <div id="node-detail-connections"></div>\n'
        '      </div>\n'
        '    </div>\n'
        '    <div id="stats"></div>\n'
        '  </div>\n'
        '  <div id="controls">\n'
        '    <button class="ctrl-btn" id="btn-reset">Reset view</button>\n'
        '    <button class="ctrl-btn" id="btn-pause">Pause</button>\n'
        '    <button class="ctrl-btn" id="btn-reheat">Reheat</button>\n'
        '    <button class="ctrl-btn" id="btn-clear">Clear filter</button>\n'
        '    <button class="ctrl-btn" id="btn-layout">DAG layout</button>\n'
        '    <button class="ctrl-btn" id="btn-pin">Pin groups</button>\n'
        '    <button class="ctrl-btn" id="btn-export">Export PNG</button>\n'
        '  </div>\n'
        '</div>\n'
        '<div id="canvas-wrap">\n'
        '  <canvas id="graph"></canvas>\n'
        '  <div id="tooltip"></div>\n'
        '</div>\n'
        '<script>\n'
        + js_data
        + _JS_LOGIC
        + '\n</script>\n</body>\n</html>'
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

def generate_from_json(json_path: Path, out_path: Path | None = None) -> Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    nodes, edges = build_graph(data)

    meta = data.get("article_metadata", {})
    title = meta.get("title") or json_path.stem

    html = generate_html(nodes, edges, title)

    if out_path is None:
        out_path = json_path.with_suffix(".graph.html")
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m tools.graph_generator <analysis.json> [output.html]")
        sys.exit(1)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    out = generate_from_json(src, dst)
    data = json.loads(src.read_text())
    nodes, edges = build_graph(data)
    print(f"Graph: {len(nodes)} nodes, {len(edges)} edges → {out}")
