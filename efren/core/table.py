"""Table — the billiards table visualizer (Efren's canvas).

Renders any task as a pool table: cushions = constraints, pockets = goals,
balls = resources/obstacles. Helps see the kick shot.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TableRead:
    task: str
    cushions: List[str] = field(default_factory=list)  # constraints to bounce off
    pockets: List[str] = field(default_factory=list)   # goals
    balls: List[str] = field(default_factory=list)     # resources / obstacles
    straight_shot: str = ""   # obvious approach
    magician_shot: str = ""   # indirect 2-3 cushion approach
    leave: str = ""           # what table looks like after


# Simple heuristic: extract constraints/goals from keywords
_CONSTRAINT_HINTS = {
    "cost": r"\b(low-cost|cheap|budget|cost|afford)\b",
    "time": r"\b(fast|quick|urgent|deadline|time)\b",
    "materials": r"\b(hardware|materials?|parts|tools|build|make)\b",
    "scale": r"\b(scale|manufacture|factory|10x|production)\b",
    "safety": r"\b(safe|safety|risk|fail)\b",
    "energy": r"\b(energy|power|electric|battery)\b",
    "precision": r"\b(precise|measurement|accuracy|purify|filter)\b",
    "regulation": r"\b(regulat|compliance|FDA|certified)\b",
}
_GOAL_HINTS = {
    "clean water": r"\b(water|purif|filter|clean)\b",
    "novelty": r"\b(novel|invent|new|creative|idea)\b",
    "automation": r"\b(automat|compiler|script)\b",
    "understanding": r"\b(understand|explain|theory)\b",
}


def analyze_task(task: str) -> TableRead:
    t = task.lower()
    cushions = [k for k, pat in _CONSTRAINT_HINTS.items() if re.search(pat, t)]
    pockets = [k for k, pat in _GOAL_HINTS.items() if re.search(pat, t)]
    if not cushions:
        cushions = ["scope", "resources", "trade-offs"]
    if not pockets:
        pockets = ["done", "elegant", "robust"]
    # naive balls extraction: split on commas/and
    balls = []
    # if task mentions hardware store parts, that's a ball
    if "hardware" in t:
        balls.append("hardware-store parts (ball)")
    if "water" in t:
        balls.append("dirty water (cue ball)")
        balls.append("clean water (8-ball)")

    # Heuristic straight vs magician shot
    straight = f"Direct build for '{task[:60]}...' using obvious method (brute-force, single-discipline)."
    magician = (
        "Kick shot: bounce off cushions "
        + ", ".join(f"[{c}]" for c in cushions[:3])
        + " → reach pockets "
        + ", ".join(pockets[:2])
        + " via indirect path (e.g., use gravity/low-pressure + soft touch vs power)."
    )
    leave = (
        "If magician shot misses, leaves opponent (next problem) with table: "
        + "self has good leave (reusable, repairable), opponent blocked by your setup."
    )
    return TableRead(task=task, cushions=cushions, pockets=pockets, balls=balls or ["cue ball (you)", "target ball"], straight_shot=straight, magician_shot=magician, leave=leave)


def render_ascii(tr: TableRead, width: int = 56) -> str:
    """Render a pool-table ASCII canvas."""
    w = width
    inner = w - 2
    lines: List[str] = []
    lines.append("+" + "=" * inner + "+")
    # pockets row
    pocket_line = "○" + " " * (inner - 2) + "○"
    lines.append("|" + pocket_line + "|  POCKETS: " + ", ".join(tr.pockets))
    lines.append("|" + " " * inner + "|")
    # cushions as top cushion
    cush_text = " CUSHIONS: " + " | ".join(tr.cushions)
    cush_text = cush_text[:inner].ljust(inner)
    lines.append("|" + cush_text + "|")
    lines.append("|" + "-" * inner + "|  <- top cushion")
    # balls area
    # cue ball
    ball_line1 = "  ● cue".ljust(inner - 12) + "  ○ target"
    ball_line1 = ball_line1.ljust(inner)
    lines.append("|" + ball_line1 + "|")
    if tr.balls:
        for b in tr.balls[:2]:
            bl = f"  · {b}"[:inner].ljust(inner)
            lines.append("|" + bl + "|")
    lines.append("|" + " " * inner + "|")
    lines.append("|" + " " * inner + "|  Straight shot: ───► (blocked)" )
    lines.append("|" + " " * inner + "|  Magician kick:  ╱╲  (2-3 cushions)")
    lines.append("+" + "=" * inner + "+")
    lines.append("  Bottom cushion: " + " | ".join(tr.cushions[::-1])[:40])
    return "\n".join(lines)


def render_markdown(tr: TableRead) -> str:
    lines = []
    lines.append(f"## 🎱 Table Read — {tr.task[:80]}")
    lines.append("")
    lines.append(f"**Task:** {tr.task}")
    lines.append("")
    lines.append(f"**Cushions (constraints to *use*, not avoid):** {', '.join(f'`{c}`' for c in tr.cushions)}")
    lines.append(f"**Pockets (goals):** {', '.join(f'`{p}`' for p in tr.pockets)}")
    if tr.balls:
        lines.append(f"**Balls (resources/obstacles):** {', '.join(tr.balls)}")
    lines.append("")
    lines.append(f"**Straight shot (obvious, often blocked):** {tr.straight_shot}")
    lines.append("")
    lines.append(f"**🎩 Magician shot (2-3 cushions):** {tr.magician_shot}")
    lines.append("")
    lines.append(f"**Leave (table after shot):** {tr.leave}")
    lines.append("")
    lines.append("```")
    lines.append(render_ascii(tr))
    lines.append("```")
    return "\n".join(lines)


def render_for_task(task: str, style_mix: Optional[str] = None) -> str:
    tr = analyze_task(task)
    if style_mix:
        extra = f"\n*Style mix hint: `{style_mix}` — see angles via those lenses.*"
    else:
        extra = ""
    return render_markdown(tr) + extra
