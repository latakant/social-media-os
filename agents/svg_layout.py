"""SVG layout engine — computes node positions for architecture diagrams.

Pure Python, no LLM. Takes nodes + phases, returns pixel coordinates
that the architecture_card_v2 template uses to draw the diagram.

Layout: phases become columns (left→right), nodes stack vertically within
each column. Edges are rendered as bezier curves between node edges.
"""

from __future__ import annotations


NODE_W = 200
NODE_H = 70


def compute_layout(
    nodes: list[dict],
    phases: list[dict],
    canvas_w: int,
    canvas_h: int,
) -> tuple[dict, dict, float, int]:
    """Return (positions, phase_labels, col_w, svg_h).

    positions     — {node_id: position_dict}
    phase_labels  — {phase_name: label_position_dict}
    col_w         — column width in SVG units (for separators)
    svg_h         — height of the SVG element
    """
    PADDING_X   = 60
    HEADER_H    = int(canvas_h * 0.18)
    FOOTER_H    = int(canvas_h * 0.05)
    LABEL_H     = 32   # phase label band height
    svg_h       = canvas_h - HEADER_H - FOOTER_H

    diagram_w   = canvas_w - 2 * PADDING_X
    node_area_h = svg_h - LABEL_H - 16   # usable vertical space for nodes

    node_by_id  = {n["id"]: n for n in nodes}

    # ── Determine column order and node membership ──────────────────────
    if not phases:
        phases = []
    if phases:
        phase_order   = [p["name"] for p in phases]
        phase_node_ids = {p["name"]: list(p.get("node_ids", [])) for p in phases}
    else:
        # Fall back to node.phase field
        seen: list[str] = []
        for n in nodes:
            ph = n.get("phase", "default")
            if ph not in seen:
                seen.append(ph)
        phase_order    = seen
        phase_node_ids = {p: [] for p in phase_order}
        for n in nodes:
            ph = n.get("phase", "default")
            if ph in phase_node_ids:
                phase_node_ids[ph].append(n["id"])

    # Any node not listed in a phase goes into the last phase
    listed = {nid for ids in phase_node_ids.values() for nid in ids}
    unlisted = [n["id"] for n in nodes if n["id"] not in listed]
    if unlisted and phase_order:
        phase_node_ids[phase_order[-1]].extend(unlisted)

    n_cols  = max(len(phase_order), 1)
    col_w   = diagram_w / n_cols

    positions: dict    = {}
    phase_labels: dict = {}

    for col_idx, phase_name in enumerate(phase_order):
        col_center_x = PADDING_X + (col_idx + 0.5) * col_w

        phase_labels[phase_name] = {
            "x":       col_center_x,
            "y":       LABEL_H // 2 + 4,
            "col_idx": col_idx,
        }

        col_node_ids = [nid for nid in phase_node_ids.get(phase_name, [])
                        if nid in node_by_id]
        n_nodes = max(len(col_node_ids), 1)

        for row_idx, nid in enumerate(col_node_ids):
            row_cy = LABEL_H + 16 + (row_idx + 0.5) * node_area_h / n_nodes
            cx = col_center_x
            cy = row_cy
            positions[nid] = {
                "x":       cx - NODE_W / 2,
                "y":       cy - NODE_H / 2,
                "cx":      cx,
                "cy":      cy,
                "w":       NODE_W,
                "h":       NODE_H,
                "right_x": cx + NODE_W / 2,
                "left_x":  cx - NODE_W / 2,
                "col_idx": col_idx,
            }

    return positions, phase_labels, col_w, svg_h


def edge_path(from_pos: dict, to_pos: dict) -> str | None:
    """Return SVG path string for an edge, or None if not renderable."""
    if from_pos["col_idx"] >= to_pos["col_idx"]:
        return None   # skip same-column and backward edges in V1
    fx  = from_pos["right_x"]
    fy  = from_pos["cy"]
    tx  = to_pos["left_x"]
    ty  = to_pos["cy"]
    gap = tx - fx
    cp1x = fx + gap * 0.45
    cp2x = tx - gap * 0.45
    return f"M {fx:.1f} {fy:.1f} C {cp1x:.1f} {fy:.1f} {cp2x:.1f} {ty:.1f} {tx:.1f} {ty:.1f}"
