"""Style registry — loads baseline styles from YAML."""

from __future__ import annotations

import pathlib
from typing import Dict

from efren.core.style import Style


def load_registry(styles_dir: pathlib.Path | None = None) -> Dict[str, Style]:
    if styles_dir is None:
        styles_dir = pathlib.Path(__file__).parent / "baselines"
    registry: Dict[str, Style] = {}
    if not styles_dir.exists():
        return registry
    for p in sorted(styles_dir.glob("*.yaml")):
        try:
            s = Style.from_yaml(p)
            registry[s.id] = s
        except Exception as e:
            print(f"[warn] failed to load style {p}: {e}")
    # also load user styles if present
    user_dir = pathlib.Path.home() / ".efren" / "styles"
    if user_dir.exists():
        for p in sorted(user_dir.glob("*.yaml")):
            try:
                s = Style.from_yaml(p)
                registry[s.id] = s
            except Exception as e:
                print(f"[warn] failed to load user style {p}: {e}")
    return registry


def list_styles(registry: Dict[str, Style]) -> str:
    lines = ["Available inventor styles:"]
    for sid, s in sorted(registry.items()):
        lines.append(f"  {sid:12} — {s.display_name} ({s.nickname or s.era or ''}) — {s.summary[:80]}")
    return "\n".join(lines)
