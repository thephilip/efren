"""Bench — Invention Bench for efren.

Scores consolidated prompts (and optionally LLM outputs) on the Efren rubric.
No LLM required for prompt-only scoring — checks structure heuristically.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import yaml
from pydantic import BaseModel


class BenchTask(BaseModel):
    id: str
    category: str
    difficulty: str = "medium"
    task: str
    constraints: List[str] = []
    expected_citations: List[str] = []
    must_flag_silent: bool = False


class BenchConfig(BaseModel):
    bench: Dict[str, Any] = {}
    tasks: List[BenchTask]
    eval: Dict[str, Any] = {}


def load_bench(path: pathlib.Path) -> BenchConfig:
    data = yaml.safe_load(path.read_text())
    return BenchConfig(**data)


@dataclass
class TaskScore:
    task_id: str
    category: str
    difficulty: str
    checks: Dict[str, bool]
    score: float  # 0..1
    details: Dict[str, str] = field(default_factory=dict)
    prompt_len: int = 0


def score_prompt(prompt: str, task: BenchTask, corpus_available: bool = True) -> TaskScore:
    """Heuristic scoring of a rendered prompt (no LLM)."""
    p = prompt.lower()
    checks: Dict[str, bool] = {}
    details: Dict[str, str] = {}

    # citation: prompt must require citation or have silent flag
    has_citation_req = "cite every" in p or "[source:" in p or "citation required" in p
    # also check if corpus silent is correctly handled — prompt contains silent instruction
    checks["citation"] = has_citation_req
    details["citation"] = "requires [source: <file> | id: <id>]" if has_citation_req else "missing citation enforcement"

    # angles: prompt must have Angles / magician shot protocol
    has_angles = "angles" in p and ("magician" in p or "kick shot" in p or "high-risk" in p)
    checks["angles"] = has_angles
    details["angles"] = "has Angles+magician" if has_angles else "missing Angles/magician"

    # table_read: cushions/pockets/leave
    has_table = "cushion" in p and "pocket" in p
    checks["table_read"] = has_table
    details["table_read"] = "cushions+pockets present" if has_table else "missing table read"

    # execution: concrete steps + falsifiable
    has_exec = "execution" in p and ("falsifiable" in p or "curie" in p or "einstein" in p)
    checks["execution"] = has_exec
    details["execution"] = "execution+falsifiable present" if has_exec else "missing execution"

    # safety
    has_safety = "safety" in p
    checks["safety"] = has_safety
    details["safety"] = "has Safety" if has_safety else "missing Safety"

    # gold citations hint — not strict, just bonus if expected_citations terms appear in prompt context
    # (corpus grounding will have them if relevant)

    score = sum(checks.values()) / len(checks) if checks else 0.0
    return TaskScore(
        task_id=task.id,
        category=task.category,
        difficulty=task.difficulty,
        checks=checks,
        score=score,
        details=details,
        prompt_len=len(prompt),
    )


def score_llm_output(output: str, task: BenchTask) -> Dict[str, bool]:
    """Score actual LLM output (if available) — stricter."""
    o = output.lower()
    checks: Dict[str, bool] = {}
    # citation: output should contain [source: ... | id: ...] or (corpus silent)
    checks["citation"] = ("[source:" in o and "| id:" in o) or "(corpus silent" in o
    # angles
    checks["angles"] = ("angle" in o or "magician" in o or "kick shot" in o) and ("high-risk" in o or "straight shot" in o)
    # table read
    checks["table_read"] = "cushion" in o and "pocket" in o
    # execution
    checks["execution"] = "step" in o and ("falsifi" in o or "experiment" in o)
    # safety
    checks["safety"] = "safety" in o or "fail" in o
    return checks


def score_llm_output_detailed(output: str, task: BenchTask) -> tuple[Dict[str, bool], Dict[str, str]]:
    """Detailed LLM scoring with expected_citations bonus."""
    checks = score_llm_output(output, task)
    details: Dict[str, str] = {}
    for k, v in checks.items():
        details[k] = "✓" if v else "✗"
    # expected citations bonus — does output mention gold terms?
    if task.expected_citations:
        o_low = output.lower()
        for term in task.expected_citations:
            if term.lower() in o_low:
                details[f"gold:{term}"] = "✓ hit"
            else:
                details[f"gold:{term}"] = "✗ miss"
                # don't fail overall, just note
    return checks, details


def score_to_float(checks: Dict[str, bool]) -> float:
    if not checks:
        return 0.0
    # only main 5 checks count for score; gold is bonus detail
    main = {k: v for k, v in checks.items() if not k.startswith("gold:")}
    return sum(main.values()) / len(main) if main else 0.0


def summarize(scores: List[TaskScore]) -> Dict[str, Any]:
    if not scores:
        return {"avg": 0.0, "count": 0}
    avg = sum(s.score for s in scores) / len(scores)
    by_cat: Dict[str, List[float]] = {}
    by_diff: Dict[str, List[float]] = {}
    for s in scores:
        by_cat.setdefault(s.category, []).append(s.score)
        by_diff.setdefault(s.difficulty, []).append(s.score)
    return {
        "avg": avg,
        "count": len(scores),
        "by_category": {k: sum(v) / len(v) for k, v in by_cat.items()},
        "by_difficulty": {k: sum(v) / len(v) for k, v in by_diff.items()},
    }
