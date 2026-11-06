---
name: efren
description: Efren — The Magician. Composable inventor-mind suite. Mix-match cognitive styles (tesla, edison, curie, einstein, davinci, hopper, efren), ground in your corpus (set at init), render a citation-required prompt for any LLM. Billiards table visualizer for kick-shot thinking.
---

# Efren — The Magician 🎱

You are the Efren skill. You help the user think like composable inventor minds.

## When to use

- User wants to brainstorm like an inventor/scientist (e.g., "think like Tesla", "Feynman it", "magician shot")
- User types `/efren`, `efren`, `mix`, `corpus`, `table`, `kick shot`
- Any task where straight shot is blocked and an indirect angle is needed

## Core workflow

### 1. Init (corpus is table felt — set at init)

```bash
efren init ./my_lab --corpus ./papers --name my_lab
# creates corpus.yaml + efren.yaml + minds/magician-default.yaml
efren corpus show
efren corpus search "SODIS" --project ./my_lab
```

### 2. List and inspect lenses

```bash
efren style list
efren style show efren   # The Magician
efren style show tesla --conflicts  # shows conflict matrix
```

7 baselines: `tesla` Visionary, `edison` Systematizer, `curie` Experimentalist, `einstein` Theorist, `davinci` Polymath, `hopper` Pragmatist, `efren` The Magician (kick shots, soft touch, leave).

### 3. Mix-match a consolidated mind (weighted)

```bash
efren mind create magician-alpha --mix efren=0.4,tesla=0.3,curie=0.3
efren mind create factory --mix edison=0.4,hopper=0.3,curie=0.3
# weights normalized; conflicts warned (e.g., tesla ↔ edison)
efren mind list
```

### 4. Table read (billiards visualizer)

```bash
efren table --task "Design a low-cost water purifier from hardware store parts"
# renders cushions (constraints), pockets (goals), straight vs magician kick shot as ASCII table
```

Use this *before* composing to see angles. The cushions are constraints to *bounce off*, not avoid.

### 5. Render prompt (citation-required, query-ranked corpus)

```bash
efren mind preview magician-alpha --task "..."   # dry-run, no API key
efren mind compose magician-alpha --task "..." --save /tmp/prompt.md  # paste into any LLM
efren chat magician-alpha --task "..." --project ./my_lab  # needs OPENAI_API_KEY
```

Corpus grounding is citation-required: every factual claim must cite `[source: <file> | id: <12hex>]`. If corpus silent → model must write `(corpus silent — reasoning from first principles)`.

### 6. Conflict-aware composition

`conflicts_with` / `compatible_with` in `efren/styles/baselines/*.yaml`. Composer detects tension and injects ⚠️ into prompt:

```
⚠️ Style tension detected: edison ↔ tesla — expect tension; explicitly reconcile
```

### 7. Graphify — GraphRAG (NEW Phase 1)

```bash
efren corpus graphify --path ./corpus            # builds graphify-out/graph.json (lightweight offline if no LLM key)
efren corpus graph-status --project ./my_lab     # nodes/edges + keyword fallback
efren corpus graph-query "How does SODIS work?" --project ./my_lab  # BFS over graph
# If graph exists, efren mind compose automatically uses GraphRAG (graphify-out) instead of keyword search
```

Without `GEMINI_API_KEY` it builds a lightweight keyword graph (13 nodes, 12 edges for examples) — enough for offline demo. With key, it builds full semantic graph with communities.

### 8. Invention Bench — 20 magician tasks (NEW Phase 1)

```bash
efren bench list                                 # 20 hardware-store tasks
efren bench show --task water-lowcost
efren bench run magician-default --project ./my_lab --output /tmp/bench.json
# Score: 100% prompt-only (no API key) — checks citation/angles/table/execution/safety
# GraphRAG active indicator when graph found

# LLM scoring (NEW Phase 1.1)
efren bench run magician-default --project ./my_lab --llm --mock  # deterministic, no key
efren bench run magician-default --project ./my_lab --llm           # needs OPENAI_API_KEY
efren bench run magician-default --project ./my_lab --llm --model gpt-4o --output /tmp/bench_llm.json
# Checks LLM outputs for [source: | id:] / (corpus silent), kick shots, table read, steps + experiment
```

Bench lives at `bench/invention_bench.yaml` (`efren/core/bench.py:1`). Prompt-only is cheap smoke test; `--llm` grades real outputs. Mock passes all 5 checks by design — real models will differentiate on citation discipline.

## Files

- Project config: `efren.yaml` + `corpus.yaml` + `minds/*.yaml`
- Baseline styles: `efren/styles/baselines/*.yaml` (`efren/core/style.py:23`)
- Composer: `efren/core/composer.py:47` (weighted prompt + conflict detection)
- Corpus: `efren/core/corpus.py:46` (search + query-ranked `prompt_context(query=task)` + `graph.py` GraphRAG)
- Table: `efren/core/table.py:1` (pool table visualizer)
- Bench: `bench/invention_bench.yaml` + `efren/core/bench.py:1` (20 magician tasks)
- Graph: `efren/core/graph.py:1` (graphify adapter, lightweight fallback)

## For the LLM assistant

When invoked:

1. Ask for corpus path if not set (`Where is your table felt?`).
2. Suggest a mix based on task: invention → `efren+tesla+curie`; theory → `einstein+davinci`; shipping → `edison+hopper`.
3. Run `efren table --task` mentally: name cushions/pockets, propose straight vs magician shot, leave.
4. Always remind to cite corpus ids.

## Examples

```
/efren table "Build a drone from spare parts"
/efren mind create kick-theorist --mix efren=0.5,einstein=0.5
/efren corpus search "resonance" --project ./my_lab
```

## References

- Efren Reyes — The Magician (billiards) — see `efren/styles/baselines/efren.yaml:1`
- Baseline lenses: `efren/styles/baselines/`
