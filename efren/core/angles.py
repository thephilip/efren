"""Angles — sample coherent-but-unavailable idea combinations from the corpus.

Lightweight, offline take on "The Alien Space of Science" (arXiv:2603.01092):
papers -> idea atoms, rank atom triplets by

    (1 - beta) * z(coherence) + beta * z(unavailability)

The paper learns both scores (coherence transformer, author-atom dual encoder).
Here both are cheap lexical proxies so it runs on any corpus with no models:

- atom           = one bullet / line / paragraph of a corpus chunk (cites its chunk id)
- coherence      = atoms must form a connected chain (shared terms, or task terms
                   as hub); scored by mean + max task-term overlap
- unavailability = atoms rarely co-occur (1 - mean pairwise Jaccard), come from
                   different sources / chunks

Fail-closed: if no atom touches the task, return [] (corpus silent).
"""

from __future__ import annotations

import itertools
import pathlib
import re
import statistics
from dataclasses import dataclass
from typing import List, Set

from efren.core.corpus import Corpus

STOP = {
    "the", "and", "for", "with", "from", "this", "that", "have", "has", "are", "was", "were",
    "been", "being", "will", "would", "could", "should", "about", "into", "over", "under",
    "your", "you", "not", "but", "all", "any", "can", "had", "also", "such", "then", "than",
    "which", "when", "what", "how", "why", "design", "task", "here", "their", "them", "they",
    "more", "less", "only", "each", "other", "some", "make", "build", "using", "used",
}


def _stem(t: str) -> str:
    # crude suffix strip so "filters"/"filter", "pumped"/"pump" link up
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def _terms(text: str) -> Set[str]:
    return {_stem(t) for t in re.findall(r"\w+", text.lower()) if len(t) > 3 and t not in STOP and not t.isdigit()}


@dataclass
class Atom:
    chunk_id: str
    source: str
    text: str
    terms: Set[str]
    relevance: float = 0.0  # task-term overlap, 0..1

    @property
    def citation(self) -> str:
        return f"[source: {pathlib.Path(self.source).name} | id: {self.chunk_id}]"


@dataclass
class Angle:
    atoms: List[Atom]
    coherence: float
    unavailability: float
    score: float = 0.0

    def render(self, idx: int) -> str:
        lines = [
            f"{idx}. score {self.score:+.2f} (coherence {self.coherence:.2f}, unavailability {self.unavailability:.2f})"
        ]
        for a in self.atoms:
            lines.append(f"   - {a.text}  {a.citation}")
        return "\n".join(lines)


def extract_atoms(corpus: Corpus, min_chars: int = 20) -> List[Atom]:
    """Split chunks into idea atoms (bullets / lines / paragraphs); skip headings."""
    atoms: List[Atom] = []
    seen: Set[str] = set()
    for c in corpus.ingest():
        for raw in re.split(r"\n\s*\n|\n(?=\s*[-*+]\s|\s*\d+[.)]\s)", c.text):
            text = " ".join(raw.split())
            text = re.sub(r"^([-*+]|\d+[.)])\s+", "", text)
            if len(text) < min_chars or text.startswith("#"):
                continue
            key = text.lower()
            if key in seen:  # chunk overlap repeats lines
                continue
            terms = _terms(text)
            if len(terms) < 2:
                continue
            seen.add(key)
            atoms.append(Atom(chunk_id=c.id, source=c.source, text=text, terms=terms))
    # chunk boundaries cut lines mid-sentence; overlap keeps the full line in the neighbour chunk
    return [a for a in atoms if not any(a is not b and a.text in b.text for b in atoms)]


def _jaccard(a: Set[str], b: Set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _connected(triplet: List[Atom], task_terms: Set[str]) -> float:
    """Fraction of atoms reachable from the first via shared terms (task terms act as hub)."""
    def linked(x: Atom, y: Atom) -> bool:
        return bool(x.terms & y.terms) or (bool(x.terms & task_terms) and bool(y.terms & task_terms))

    reached = {0}
    frontier = [0]
    while frontier:
        i = frontier.pop()
        for j in range(len(triplet)):
            if j not in reached and linked(triplet[i], triplet[j]):
                reached.add(j)
                frontier.append(j)
    return len(reached) / len(triplet)


def _z(values: List[float]) -> List[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mu = statistics.fmean(values)
    sd = statistics.pstdev(values)
    return [(v - mu) / sd if sd else 0.0 for v in values]


def sample_angles(
    corpus: Corpus,
    task: str,
    top_k: int = 5,
    beta: float = 0.7,
    k: int = 3,
    max_atoms: int = 60,
) -> List[Angle]:
    """Rank k-atom combinations from the corpus for a task. Deterministic."""
    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must be in [0, 1]")
    task_terms = _terms(task)
    atoms = extract_atoms(corpus)
    if len(atoms) < k or not task_terms:
        return []
    for a in atoms:
        a.relevance = len(a.terms & task_terms) / len(task_terms)
    if not any(a.relevance > 0 for a in atoms):
        return []  # corpus silent for this task
    # keep most task-relevant atoms first, corpus order as tie-break (stable sort)
    atoms = sorted(atoms, key=lambda a: a.relevance, reverse=True)[:max_atoms]

    pool: List[Angle] = []
    for combo in itertools.combinations(atoms, k):
        combo = list(combo)
        rels = [a.relevance for a in combo]
        if max(rels) == 0:
            continue  # need at least one anchor to the task
        if _connected(combo, task_terms) < 1:
            continue  # coherence floor: every atom must chain to the others
        coherence = 0.7 * statistics.fmean(rels) + 0.3 * max(rels)
        pair_sim = statistics.fmean(_jaccard(x.terms, y.terms) for x, y in itertools.combinations(combo, 2))
        sources = len({a.source for a in combo})
        chunks = len({a.chunk_id for a in combo})
        unavailability = (1 - pair_sim) + 0.25 * (sources - 1) / (k - 1) + 0.1 * (chunks - 1) / (k - 1)
        pool.append(Angle(atoms=combo, coherence=coherence, unavailability=unavailability))
    if not pool:
        return []

    zc = _z([p.coherence for p in pool])
    zu = _z([p.unavailability for p in pool])
    for p, c, u in zip(pool, zc, zu):
        p.score = (1 - beta) * c + beta * u
    pool.sort(key=lambda p: p.score, reverse=True)

    # diversity: don't let one atom dominate the top list
    picked: List[Angle] = []
    uses: dict[int, int] = {}
    for p in pool:
        if any(uses.get(id(a), 0) >= 2 for a in p.atoms):
            continue
        picked.append(p)
        for a in p.atoms:
            uses[id(a)] = uses.get(id(a), 0) + 1
        if len(picked) >= top_k:
            break
    return picked


def angles_context(corpus: Corpus, task: str, top_k: int = 3, beta: float = 0.7) -> str | None:
    """Prompt block of unseen angles, or None if corpus is silent for the task."""
    angles = sample_angles(corpus, task, top_k=top_k, beta=beta)
    if not angles:
        return None
    return "\n".join(a.render(i) for i, a in enumerate(angles, 1))
