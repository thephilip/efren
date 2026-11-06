"""Composer — mix-match styles into a consolidated inventor mind."""

from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import BaseModel

from efren.core.style import Style


class WeightedStyle(BaseModel):
    style_id: str
    weight: float  # 0..1, normalized by Composer


class Composer:
    """Takes multiple Styles with weights and produces a consolidated system prompt."""

    def __init__(self, registry: Dict[str, Style]):
        self.registry = registry

    def normalize(self, specs: List[WeightedStyle]) -> List[WeightedStyle]:
        total = sum(s.weight for s in specs)
        if total == 0:
            raise ValueError("total weight cannot be 0")
        return [WeightedStyle(style_id=s.style_id, weight=s.weight / total) for s in specs]

    def parse_mix(self, mix_str: str) -> List[WeightedStyle]:
        """Parse 'tesla=0.5,efren=0.3,curie=0.2' or 'tesla,curie' (equal weights)."""
        if not mix_str.strip():
            raise ValueError("empty mix string")
        parts = [p.strip() for p in mix_str.split(",") if p.strip()]
        specs: List[WeightedStyle] = []
        for p in parts:
            if "=" in p:
                sid, w = p.split("=", 1)
                specs.append(WeightedStyle(style_id=sid.strip(), weight=float(w.strip())))
            else:
                specs.append(WeightedStyle(style_id=p, weight=1.0))
        # validate ids
        for s in specs:
            if s.style_id not in self.registry:
                raise ValueError(f"unknown style '{s.style_id}'. Available: {', '.join(sorted(self.registry))}")
        return self.normalize(specs)

    def compose_prompt(
        self,
        weighted: List[WeightedStyle],
        corpus_context: str | None = None,
        task: str | None = None,
        extra_instructions: str | None = None,
        angles_context: str | None = None,
    ) -> str:
        weighted = self.normalize(weighted)
        # sort by weight desc for deterministic prompt ordering
        weighted_sorted = sorted(weighted, key=lambda x: x.weight, reverse=True)

        primary = self.registry[weighted_sorted[0].style_id]

        lines: List[str] = []
        lines.append("# EFREN — Consolidated Inventor Mind")
        lines.append(f"Primary lens: **{primary.display_name}** ({primary.id}) — weight {weighted_sorted[0].weight:.2f}")
        lines.append(f"Composition: {', '.join(f'{w.style_id}={w.weight:.2f}' for w in weighted_sorted)}")
        conflicts = self.detect_conflicts(weighted_sorted)
        if conflicts:
            lines.append("")
            lines.append("⚠️ **Style tension detected (conflict matrix):**")
            for c in conflicts:
                lines.append(f"- {c} — expect tension; explicitly reconcile or pick a primary lens.")
            lines.append("")
        lines.append("")
        lines.append("> You are not impersonating these figures. You are emulating their *problem-solving processes*")
        lines.append("> to find non-obvious solutions — the Efren 'Magician' way: see angles others miss.")
        lines.append("")

        if task:
            lines.append(f"## Task\n{task}\n")

        lines.append("## How to think (consolidated filters)")
        # merge reasoning filters weighted order
        seen = set()
        idx = 1
        for w in weighted_sorted:
            style = self.registry[w.style_id]
            for f in style.reasoning_filters:
                key = f.question
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"{idx}. [{style.id} {w.weight:.2f}] {f.step}: *{f.question}*")
                idx += 1
        lines.append("")

        lines.append("## Heuristics to apply (weighted)")
        for w in weighted_sorted:
            style = self.registry[w.style_id]
            for h in style.heuristics:
                lines.append(f"- [{style.id} {w.weight:.2f}] **{h.name}**: {h.prompt_fragment}")
        lines.append("")

        lines.append("## Style lenses (detailed)")
        for w in weighted_sorted:
            style = self.registry[w.style_id]
            lines.append(style.prompt_block(weight=w.weight))
            lines.append("")

        if corpus_context:
            lines.append("## Corpus grounding (set at init) — CITATION REQUIRED")
            lines.append("This is your table felt — you cannot invent facts off it.")
            lines.append("- Cite EVERY factual claim as `[source: <filename> | id: <id>]` using the ids above.")
            lines.append("- If corpus is silent for the task, explicitly write `(corpus silent — reasoning from first principles)` and flag uncertainty.")
            lines.append("- Prefer corpus facts over prior knowledge; if conflict, note it.")
            lines.append("```")
            lines.append(corpus_context[:8000])
            lines.append("```")
            lines.append("")

        if angles_context:
            lines.append("## Unseen angles (coherent but unavailable corpus combinations)")
            lines.append("Corpus ideas that rarely appear together yet still hook to the task — kick-shot seeds.")
            lines.append("- Consider at least one in your Angles step; say why it works or why you rejected it.")
            lines.append("- Cite the atoms you use with their ids.")
            lines.append("```")
            lines.append(angles_context[:4000])
            lines.append("```")
            lines.append("")

        lines.append("## Output protocol (Efren table logic)")
        lines.append("1. **Angles**: list 2-3 non-obvious approaches (the 'magician shots') — include one high-risk/high-reward.")
        lines.append("2. **Table read**: assess constraints like a billiards table — what are the cushions, pockets, and opponent's likely leave?")
        lines.append("3. **Shot selection**: pick one angle, justify via the consolidated filters above.")
        lines.append("4. **Execution**: give concrete steps, with falsifiable checks (à la Curie/Einstein). Cite corpus ids for any factual claim.")
        lines.append("5. **Safety**: note where this emulation may be wrong and whether corpus was silent; suggest an experiment to verify.")
        lines.append("")

        if extra_instructions:
            lines.append(f"## Additional instructions\n{extra_instructions}\n")

        lines.append("---")
        lines.append("Remember: be the magician — find the *kick shot* nobody else saw, but explain it so an apprentice could execute it.")

        return "\n".join(lines)

    def detect_conflicts(self, weighted: List[WeightedStyle]) -> List[str]:
        """Detect style conflicts (hersona-style). Returns warning strings."""
        warnings: List[str] = []
        ids = {w.style_id for w in weighted}
        for w in weighted:
            style = self.registry[w.style_id]
            for c in style.conflicts_with:
                if c in ids:
                    # only report once per unordered pair
                    if w.style_id < c:
                        warnings.append(f"{w.style_id} ↔ {c}: {style.display_name} conflicts with {self.registry[c].display_name}")
                    else:
                        # avoid duplicate if counterpart also lists it
                        # still report if not already reported
                        pair = f"{c} ↔ {w.style_id}"
                        rev = f"{w.style_id} ↔ {c}"
                        if pair not in warnings and rev not in warnings:
                            warnings.append(f"{c} ↔ {w.style_id}: {self.registry[c].display_name} conflicts with {style.display_name}")
        # dedupe
        seen = set()
        uniq = []
        for w in warnings:
            if w not in seen:
                seen.add(w)
                uniq.append(w)
        return uniq

    def blend_traits(self, weighted: List[WeightedStyle]) -> Dict[str, float]:
        """Return a trait blend for introspection / UI."""
        trait_scores: Dict[str, float] = {}
        for w in weighted:
            style = self.registry[w.style_id]
            for s in style.strengths:
                trait_scores[s] = trait_scores.get(s, 0) + w.weight
        return dict(sorted(trait_scores.items(), key=lambda x: x[1], reverse=True))
