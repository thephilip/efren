# Efren — The Magician

> **Composable inventor-mind suite for LLMs.** Mix-match cognitive styles, ground in your corpus, render a consolidated system prompt for *any* LLM.

Named for **Efren Reyes — "The Magician"** — the pool legend who sees kick shots nobody else sees. Efren is the patron style: when the straight shot is blocked, find the 3-cushion angle.

---

## What it is

A **suite/framework** that lets you:

1. **Set corpus at init** — `efren init --corpus ./my_papers` creates a grounded knowledge base. No corpus = generic mind; with corpus = claims are cited/constrained.
2. **Use baseline inventor styles** — 7 shipped lenses, each with heuristics, reasoning filters, and vocabulary:
   - `tesla` — The Visionary (mental simulation, resonance)
   - `edison` — The Systematizer (parameter sweeps, factory)
   - `curie` — The Experimentalist (isolation, measurement)
   - `einstein` — The Theorist (invariants, Gedankenexperiments)
   - `davinci` — The Polymath (analogy, draw-to-think)
   - `hopper` — The Pragmatist (compiler, debug, automate)
   - `efren` — **The Magician** (kick shots, soft touch, leave thinking)
3. **Mix-match into a consolidated inventor** — `tesla=0.4,efren=0.4,curie=0.2` → one weighted system prompt. Composition is normalized, ordered, and rendered deterministically.
4. **Stay LLM-agnostic** — efren *renders prompts*, not model calls. Works with OpenAI, Anthropic, local LLMs, or opencode. Optional `efren chat` for OpenAI-compatible endpoints.

```
Your Corpus (set at init)  ──┐
                             ├──> Composer ──> Consolidated System Prompt ──> Any LLM
Baseline Styles (mixable)  ──┘          (weighted heuristics + corpus grounding)
```

---

## Quickstart

### Install

```bash
pip install -e .          # from ~/Downloads/_project/efren
# or: pip install efren
efren --help
```

### CLI — 60 seconds

```bash
# 1. Init project with corpus (corpus is SET AT INIT)
efren init ./my_lab --corpus ./my_papers --name my_lab

# 2. See baseline styles
efren style list
efren style show efren   # inspect The Magician

# 3. Create a composable mind (mix-match)
efren mind create magician-alpha --mix efren=0.4,tesla=0.3,curie=0.3 \
  --desc "Creative angles + visual sim + precision"

# 4. Preview the consolidated prompt (no API key)
efren mind preview magician-alpha --task "Design a low-cost water purifier from hardware store parts"

# 5. Render full prompt for any LLM
efren mind compose magician-alpha --task "Design a low-cost water purifier" --save /tmp/prompt.md
# paste /tmp/prompt.md into ChatGPT / Claude / local model

# 6. (Optional) Call OpenAI directly
export OPENAI_API_KEY=sk-...
efren chat magician-alpha --task "Design a low-cost water purifier"
```

### Python API

```python
from pathlib import Path
from efren.core.corpus import Corpus, CorpusConfig, CorpusSource
from efren.core.mind import Mind
from efren.styles.registry import load_registry
from efren.core.table import render_for_task
from efren.core.llm import build_messages

registry = load_registry()  # 7 baselines
corpus = Corpus(CorpusConfig(name="demo", sources=[
    CorpusSource(path="./my_papers")
]), root=Path("."))

# Table read first — see the cushions/pockets before shooting
print(render_for_task("Design a low-cost water purifier"))

# Mix-match: weighted composition (conflicts warned automatically)
mind = Mind.from_mix_string(
    name="magician-v1",
    mix="efren=0.4,tesla=0.3,curie=0.3",
    registry=registry,
)
# corpus search is now query-ranked + citation-required
hits = corpus.search("SODIS", top_k=3)  # each hit has .id for citation
print(hits[0].id)  # b3d85b07b01f

# Render corpus-grounded prompt for any task (silent corpus flagged)
system_prompt = mind.render_prompt(registry=registry, corpus=corpus,
                                   task="Design a low-cost water purifier")

# Use with any LLM
messages = build_messages(system_prompt, "Design a low-cost water purifier")
# -> [{"role": "system", ...}, {"role": "user", ...}]
```

See `examples/01_quickstart.py` and `examples/02_cli_walkthrough.sh`.

### Phase 0 — new (citation, table, conflicts, skill)

```bash
# Table visualizer — see straight vs magician kick shot
efren table "Design a low-cost water purifier from hardware store parts"
efren table --task "Build a drone from spare parts" --save /tmp/table.md

# Corpus search — citation ids for every claim
efren corpus search "SODIS" --project ./my_lab
# → [source: notes.md | id: b3d85b07b01f]  /path/to/notes.md
#    snippet...
# Compose now requires citations and flags corpus silence:
efren mind compose magician-alpha --task "quantum reactor" --project ./my_lab
# → (corpus silent for query 'quantum reactor' — no matching chunks. Reason from first principles ...)

# Conflict-aware mixer — warns when styles tension
efren mind create clash --mix tesla=0.5,edison=0.5
# → ⚠️  Style tension detected: edison ↔ tesla — expect tension; explicitly reconcile
efren style show tesla  # shows Conflicts with: / Compatible with:

# Opencode skill — use inside opencode as /efren
# Skill lives at .opencode/skills/efren/SKILL.md — invoke with /efren in any opencode session
```

### Phase 1 — new (GraphRAG + Invention Bench)

```bash
# Build graphify graph (lightweight offline if no GEMINI_API_KEY, full with key)
efren corpus graphify --path ./corpus --project ./my_lab
# → graphify-out/graph.json (13 nodes, 12 edges offline demo)
efren corpus graph-status --project ./my_lab
efren corpus graph-query "How does SODIS work?" --project ./my_lab
# GraphRAG auto-used in prompt — efren mind compose now pulls from graph if present

# Invention Bench — 20 hardware-store tasks only the Magician can ace
efren bench list
efren bench run magician-default --project ./my_lab --output /tmp/bench.json
# Score: 100% prompt-only | By category / By difficulty | GraphRAG active indicator
```

### Phase 1.1 — new (LLM scoring)

```bash
# Prompt-only (no key, as above) checks the *prompt* structure
efren bench run magician-default --project ./my_lab

# LLM scoring — calls the LLM for each of 20 tasks and grades *outputs*
efren bench run magician-default --project ./my_lab --llm --mock  # deterministic, no key (CI)
# Prompt Score: 100.00% | LLM Score: 100.00% | By category (LLM) | Worst/Best (LLM)

efren bench run magician-default --project ./my_lab --llm  # requires OPENAI_API_KEY
efren bench run magician-default --project ./my_lab --llm --model gpt-4o --output /tmp/bench_llm.json
# JSON includes prompt_score, llm_score, llm_checks, llm_output (truncated) per task
```

See `bench/invention_bench.yaml` (20 tasks) and `efren/core/bench.py:50`, `efren/core/graph.py:1`, `efren/core/llm.py:17` (mock + OpenAI).

---

### Phase 1.2 — new (unseen angles)

Offline take on [*The Alien Space of Science*](https://arxiv.org/abs/2603.01092): split the corpus into idea atoms and rank triplets that are **coherent** (they chain together and hook to the task) but **unavailable** (they rarely co-occur). Lexical proxies only, so no models or keys are needed.

```bash
efren corpus angles "Design a water filter that removes bacteria" --project ./my_lab --top 5 --beta 0.7
# 1. score +0.82 (coherence 0.52, unavailability 1.12)
#    - Ceramic filters with 0.2 micron pores remove bacteria ...  [source: notes.md | id: 204cb7f30484]
#    - Sunlight heats water in black bottles until pathogens die  [source: more.md | id: 519c72a0df03]
#    - Copper vessels kill bacteria by releasing ions over hours  [source: notes.md | id: 204cb7f30484]

# Inject the top N into the prompt as kick-shot seeds (opt-in)
efren mind compose magician-alpha --task "..." --angles 3 --project ./my_lab
```

`--beta 0` = safest combos, `--beta 1` = most alien. Silent if no atom touches the task. See `efren/core/angles.py`.

A/B it on the bench with the `claude` CLI (uses the CLI's own login, no API key) and a blind pairwise judge:

```bash
# bench/corpus/field_notes.md is a shared cross-domain corpus; point a project's corpus.yaml at it
efren bench run magician-default --project ./lab --llm --provider claude --angles 0 -o a0.json
efren bench run magician-default --project ./lab --llm --provider claude --angles 3 -o a3.json
efren bench judge a0.json a3.json -o judge.json   # novelty + feasibility 1-5, wins, position-swapped
```

---

## Corpus — set at init (now citation-required + query-ranked)

```bash
efren init ./my_lab --corpus ./papers,./notes.md
# creates ./my_lab/corpus.yaml + ./my_lab/efren.yaml + ./my_lab/minds/magician-default.yaml
cat ./my_lab/corpus.yaml
efren corpus show --project ./my_lab
efren corpus ingest --project ./my_lab
efren corpus search "SODIS" --project ./my_lab  # keyword-ranked, shows [source: file | id: 12hex]
```

Corpus grounding is now **query-ranked** (`prompt_context(query=task)`) and **citation-required**: every factual claim must cite `[source: <file> | id: <id>]`. If no chunk matches the query, the prompt injects `(corpus silent for query '...' — no matching chunks. Reason from first principles and flag as (corpus silent))` — fail-closed, not open.

Edit `corpus.yaml` to add sources — efren chunks and injects them into the prompt (vector search via `chromadb` is optional, `pip install 'efren[embeddings]'`).

---

## Mix-matching minds

Mix string grammar: `style_id[=weight],...` — weights are normalized.

```bash
efren mind create kick-theorist --mix efren=0.5,einstein=0.5
efren mind create factory-magician --mix edison=0.4,hopper=0.3,efren=0.3
efren mind create polymath --mix davinci=0.6,tesla=0.2,curie=0.2
efren mind create pure-magician --mix efren=1.0
```

Rendered prompt includes:
- Consolidated reasoning filters (deduped, weight-ordered)
- Weighted heuristics
- Full style lens blocks
- Corpus grounding block
- Efren output protocol (Angles → Table read → Shot → Execution → Safety)

Minds are YAML — versionable, shareable:

```bash
cat minds/magician-alpha.yaml
# share it, commit it, PR it
```

---

## Baseline styles

| ID | Name | Nickname | Core move |
|---|---|---|---|
| `tesla` | Nikola Tesla | The Visionary | Mental simulation, resonance tuning |
| `edison` | Thomas Edison | The Systematizer | Parameter sweeps, factory |
| `curie` | Marie Curie | The Experimentalist | Purify signal, measure |
| `einstein` | Albert Einstein | The Theorist | Invariants, thought experiments |
| `davinci` | Leonardo da Vinci | The Polymath | Analogy transfer, draw to think |
| `hopper` | Grace Hopper | The Pragmatist | Compile, debug, automate |
| `efren` | Efren Reyes | **The Magician** | Kick shots, soft touch, leave |

Add your own: drop a YAML in `~/.efren/styles/my_style.yaml` matching the schema in `efren/styles/baselines/efren.yaml` — it auto-loads.

---

## Project layout

```
efren/
  .opencode/skills/efren/  # opencode skill (/efren)
  efren/
    core/       # corpus (search+citation+graph), style (conflicts), composer, mind, table, bench, llm
    styles/baselines/  # 7 YAML lenses (with conflicts_with / compatible_with)
    cli/        # typer CLI (table, corpus search/graph, bench, conflict warnings)
    prompts/
  bench/        # invention_bench.yaml (20 tasks) ← Phase 1
  config/       # example configs
  examples/     # quickstart + corpus sample
  graphify-out/ # ← generated by efren corpus graphify (GraphRAG)
  minds/        # created at init (per-project)
  tests/
  pyproject.toml
```

---

## Efren's Table Logic (output protocol)

Every consolidated prompt asks the LLM to:

1. **Angles** — 2-3 non-obvious approaches (one high-risk/high-reward)
2. **Table read** — cushions/pockets/opponent (constraints/resources/adversary)
3. **Shot selection** — pick one, justify via filters
4. **Execution** — concrete steps + falsifiable checks
5. **Safety** — where it may be wrong + experiment to verify

---

## Development

```bash
pip install -e '.[dev]'
pytest
ruff check efren
```

---

## Why "Efren"?

Pool's straight shot is the obvious solution. The Magician wins with what others don't see — the bank, the combo, the deliberate safety that sets up the next rack. That's the framework's job: find the angle, keep the touch soft, leave the table better than you found it.

*No billiards expertise required. Just bring your corpus and pick your magicians.*
