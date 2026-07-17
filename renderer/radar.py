"""Shared radar (spider) chart of the 8 review dimensions, gold-on-dark.

Used by both the newsletter and the carousel so the visual matches across
surfaces. The SVG carries a viewBox, so callers scale it via CSS width.
"""
import math

# Short axis labels for the radar chart (the 8 review dimensions).
DIM_SHORT = {
    "source_rigor": "Sources",
    "factual_accuracy": "Exactitude",
    "reasoning_structure": "Raisonnement",
    "approach_transparency": "Transparence",
    "context_completeness": "Contexte",
    "treatment_fairness": "Équité",
    "clarity": "Clarté",
    "angle_originality": "Originalité",
}


def radar_svg(dims) -> str:
    """Radar (spider) chart of the review dimensions (score 1–5), gold on dark —
    the visual breakdown of the review. One axis per dimension. Returns "" when
    there are no dimensions."""
    if not dims:
        return ""
    n = len(dims)
    cx, cy, R = 210.0, 158.0, 96.0

    def pt(i, r):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    def poly(r_of):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, r_of(i)) for i in range(n)))

    rings = "".join(
        f'<polygon points="{poly(lambda i, rr=R*s/5: rr)}" fill="none" stroke="#2b2b2b" stroke-width="1"/>'
        for s in range(1, 6)
    )
    axes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#2b2b2b" stroke-width="1"/>'
        for x, y in (pt(i, R) for i in range(n))
    )
    data = poly(lambda i: R * dims[i].score / 5)
    shape = f'<polygon points="{data}" fill="rgba(212,170,0,0.22)" stroke="#d4aa00" stroke-width="2"/>'
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#d4aa00"/>'
        for x, y in (pt(i, R * dims[i].score / 5) for i in range(n))
    )
    labels = []
    for i in range(n):
        lx, ly = pt(i, R + 16)
        anchor = "middle" if abs(lx - cx) < 3 else ("start" if lx > cx else "end")
        short = DIM_SHORT.get(dims[i].dimension, dims[i].label)
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
            f'font-size="11" fill="#9a9a9a" font-family="Helvetica,Arial,sans-serif">{short} '
            f'<tspan fill="#d4aa00" font-weight="700">{dims[i].score}</tspan></text>'
        )
    return (
        '<svg viewBox="0 0 420 300" width="420" height="300" xmlns="http://www.w3.org/2000/svg">'
        + rings + axes + shape + dots + "".join(labels) + '</svg>'
    )
