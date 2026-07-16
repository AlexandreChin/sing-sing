"""Deterministic 'naive' vector-art generator for carousel covers.

Every style returns inline SVG *inner* markup sized to a 1080x1350 viewBox, so it
drops straight into a full-bleed background <svg>. No colour/opacity is set here —
the template owns stroke + opacity. Same seed_text -> same art (reproducible);
`cover_art` also picks the *style* deterministically from the seed.
"""
import hashlib
import math
from random import Random

W, H = 1080, 1350


def _seed(seed_text: str) -> Random:
    h = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16)
    return Random(h)


def constellation(seed_text: str) -> str:
    """A node/edge graph — echoes the product's own node-graph analysis."""
    r = _seed(seed_text)
    n = r.randint(11, 16)
    cols, rows = 4, 5
    pts = []
    for i in range(n):
        cx = (i % cols + 0.5) / cols * W + r.uniform(-90, 90)
        cy = (i // cols + 0.5) / rows * H + r.uniform(-90, 90)
        pts.append((cx, cy))
    parts = []
    for i, (x1, y1) in enumerate(pts):
        near = sorted(range(len(pts)), key=lambda j: (pts[j][0] - x1) ** 2 + (pts[j][1] - y1) ** 2)
        for j in near[1:1 + r.randint(1, 2)]:
            x2, y2 = pts[j]
            parts.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')
    for (x, y) in pts:
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.randint(6, 16)}"/>')
    return "".join(parts)


def contours(seed_text: str) -> str:
    """Stacked topographic / sound-wave lines."""
    r = _seed(seed_text)
    lines = r.randint(7, 10)
    amp = r.uniform(60, 120)
    parts = []
    for k in range(lines):
        base = (k + 0.5) / lines * H
        phase = r.uniform(0, math.tau)
        freq = r.uniform(1.4, 2.6)
        pts = []
        for sx in range(0, W + 1, 40):
            t = sx / W
            y = base + amp * math.sin(t * math.tau * freq + phase) * (0.5 + 0.5 * math.sin(t * math.pi))
            pts.append(f"{sx},{y:.0f}")
        parts.append(f'<polyline points="{" ".join(pts)}"/>')
    return "".join(parts)


def orbits(seed_text: str) -> str:
    """Concentric rotated ellipses with bodies sitting on them."""
    r = _seed(seed_text)
    cx, cy = W * r.uniform(0.4, 0.62), H * r.uniform(0.42, 0.6)
    rings = r.randint(3, 5)
    parts = []
    for k in range(rings):
        rx = (k + 1) / rings * r.uniform(360, 520)
        ry = rx * r.uniform(0.55, 0.9)
        rot = r.uniform(0, 180)
        parts.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" '
                     f'transform="rotate({rot:.0f} {cx:.0f} {cy:.0f})"/>')
        ang = r.uniform(0, math.tau)
        bx = cx + rx * math.cos(ang) * math.cos(math.radians(rot)) - ry * math.sin(ang) * math.sin(math.radians(rot))
        by = cy + rx * math.cos(ang) * math.sin(math.radians(rot)) + ry * math.sin(ang) * math.cos(math.radians(rot))
        parts.append(f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r.randint(10, 22)}"/>')
    parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r.randint(20, 34)}"/>')
    return "".join(parts)


STYLES = {"constellation": constellation, "contours": contours, "orbits": orbits}


def pick_style(seed_text: str) -> str:
    """Deterministically choose a style key from the seed (sorted keys = stable)."""
    keys = sorted(STYLES)
    idx = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % len(keys)
    return keys[idx]


def cover_art(seed_text: str) -> str:
    """Inner SVG markup of the seed-picked style for this seed."""
    return STYLES[pick_style(seed_text)](seed_text)
