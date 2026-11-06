"""Mind — a persisted, composable inventor mind."""

from __future__ import annotations

import pathlib
import datetime
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field

from efren.core.composer import WeightedStyle
from efren.core.style import Style
from efren.core.corpus import Corpus
from efren.core.composer import Composer
from efren.core.angles import angles_context


class Mind(BaseModel):
    name: str  # e.g., "magician-alpha"
    description: str = ""
    composition: List[WeightedStyle]  # mix
    corpus_ref: Optional[str] = None  # path to corpus.yaml or name
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    extra_instructions: Optional[str] = None

    def save(self, path: pathlib.Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=True))

    @classmethod
    def load(cls, path: pathlib.Path) -> "Mind":
        return cls(**yaml.safe_load(path.read_text()))

    def render_prompt(
        self,
        registry: dict[str, Style],
        corpus: Corpus | None = None,
        task: str | None = None,
        angles: int = 0,
        beta: float = 0.7,
    ) -> str:
        composer = Composer(registry)
        # use task as query for corpus ranking (citation-aware grounding)
        ctx = corpus.prompt_context(query=task) if corpus and task else (corpus.prompt_context() if corpus else None)
        # opt-in: alien-space style combinations (efren/core/angles.py)
        actx = angles_context(corpus, task, top_k=angles, beta=beta) if corpus and task and angles > 0 else None
        return composer.compose_prompt(
            weighted=self.composition,
            corpus_context=ctx,
            task=task,
            extra_instructions=self.extra_instructions,
            angles_context=actx,
        )

    @classmethod
    def from_mix_string(
        cls,
        name: str,
        mix: str,
        registry: dict[str, Style],
        description: str = "",
        extra_instructions: str | None = None,
    ) -> "Mind":
        composer = Composer(registry)
        weighted = composer.parse_mix(mix)
        return cls(name=name, description=description, composition=weighted, extra_instructions=extra_instructions)
