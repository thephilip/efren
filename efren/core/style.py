"""Style — a reusable cognitive lens / inventor style."""

from __future__ import annotations

import pathlib
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class Heuristic(BaseModel):
    name: str
    description: str
    prompt_fragment: str  # injected into system prompt


class ReasoningFilter(BaseModel):
    step: str
    question: str  # e.g., "What is the simplest physical mechanism?"


class Style(BaseModel):
    id: str  # e.g., "tesla"
    display_name: str
    nickname: str | None = None
    era: str | None = None
    domain: List[str] = Field(default_factory=list)
    summary: str
    # cognitive traits
    heuristics: List[Heuristic] = Field(default_factory=list)
    reasoning_filters: List[ReasoningFilter] = Field(default_factory=list)
    vocabulary: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    conflicts_with: List[str] = Field(default_factory=list)  # ids that tension with this style
    compatible_with: List[str] = Field(default_factory=list)
    # prompting
    system_preamble: str = ""  # core identity paragraph
    style_directives: str = ""  # how to speak/reason
    example_traces: List[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: pathlib.Path) -> "Style":
        data = yaml.safe_load(path.read_text())
        return cls(**data)

    def to_yaml(self, path: pathlib.Path) -> None:
        path.write_text(yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=True))

    def prompt_block(self, weight: float = 1.0) -> str:
        """Render this style as a prompt block for composition. Weight affects emphasis note."""
        w = f" (weight: {weight:.2f})" if weight != 1.0 else ""
        lines = [
            f"## Style: {self.display_name} [{self.id}]{w}",
            f"*{self.summary}*",
            "",
            self.system_preamble,
            "",
            "Heuristics:",
        ]
        for h in self.heuristics:
            lines.append(f"- **{h.name}**: {h.description} -> {h.prompt_fragment}")
        if self.reasoning_filters:
            lines.append("")
            lines.append("Reasoning filters (apply in order):")
            for i, f in enumerate(self.reasoning_filters, 1):
                lines.append(f"{i}. {f.step}: *{f.question}*")
        if self.vocabulary:
            lines.append("")
            lines.append(f"Preferred vocabulary/analogies: {', '.join(self.vocabulary)}")
        if self.style_directives:
            lines.append("")
            lines.append(f"Style directives: {self.style_directives}")
        return "\n".join(lines)
