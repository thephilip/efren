"""LLM adapter — pluggable, no hard dependency. Returns system prompt + helpers."""

from __future__ import annotations

import os
from typing import List, Dict, Optional


def build_messages(system_prompt: str, user_task: str, history: List[Dict[str, str]] | None = None) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        msgs.extend(history)
    msgs.append({"role": "user", "content": user_task})
    return msgs


def call_openai(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Optional OpenAI-compatible call. Requires `openai` package and API key."""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError("openai package not installed. pip install 'efren[openai]'") from e

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)
    resp = client.chat.completions.create(model=model, messages=messages)  # type: ignore[arg-type]
    return resp.choices[0].message.content or ""


def call_mock(messages: List[Dict[str, str]], task: str = "") -> str:
    """Deterministic mock LLM — returns a template that passes bench checks.

    Useful for `efren bench run --llm --mock` and CI without API keys.
    """
    # extract corpus citations from system prompt if present
    sys = messages[0]["content"] if messages else ""
    has_citation = "[source:" in sys
    citation_snippet = "[source: notes.md | id: b3d85b07b01f]"
    if has_citation:
        # pull first citation header
        import re

        m = re.search(r"\[source:.*?\| id:.*?\]", sys)
        if m:
            citation_snippet = m.group(0)
    return f"""## Angles
- Straight shot: obvious hardware-store build (blocked by cost).
- Magician shot (2 cushions): kick off cost + materials → gravity SODIS boost {citation_snippet}
- High-risk: vapor-phase filtration with waste heat.

## Table read
Cushions: cost, materials, safety. Pockets: clean water, <$5. Leave: reusable, repairable. Cushion English applied.

## Shot selection
Magician shot wins via [efren 0.40] Angle Hunt + [curie 0.30] Purification.

## Execution
1. Build ceramic pre-filter {citation_snippet}
2. SODIS boost step: PET + reflector, 2h cloudy.
3. Falsifiable check: test 1L/min flow, coliform count <1 CFU/100ml (curie measurement).

## Safety
(corpus silent for quantum parts) — verify with field test; failure mode: clogged filter → safe bypass.
(citation: {citation_snippet})
"""


def call_llm(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    mock: bool = False,
    task: str = "",
) -> str:
    """Unified entry: mock or OpenAI."""
    if mock:
        return call_mock(messages, task=task)
    return call_openai(messages, model=model)


def dry_run_preview(system_prompt: str, user_task: str, max_chars: int = 4000) -> str:
    """Return a preview without calling any LLM — useful for `efren mind preview`."""
    preview = f"=== SYSTEM PROMPT ({len(system_prompt)} chars) ===\n{system_prompt[:max_chars]}\n"
    if len(system_prompt) > max_chars:
        preview += f"... [truncated {len(system_prompt)-max_chars} chars]\n"
    preview += f"\n=== USER TASK ===\n{user_task}\n"
    preview += "\n=== MESSAGES (ready for any LLM) ===\nUse build_messages() or copy system+user into your LLM.\n"
    return preview
