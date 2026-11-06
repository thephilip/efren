# Efren Roadmap — The Magician's Table

> **Efren — composable inventor-mind suite for LLMs.** Corpus is table felt (set at init), baseline styles are lenses, mix-matching is the kick shot.
> Project root: `~/Downloads/_project/efren` · Named for **Efren Reyes — "The Magician"** (`efren/styles/baselines/efren.yaml:1`).

---

## Philosophy in one shot

| Straight shot (what others do) | Magician shot (Efren) |
|---|---|
| Generic persona prompt | Weighted heuristic *filters* (`efren/core/style.py:23`, `composer.py:72`) |
| Optional RAG | **Corpus-at-init, fail-closed**: `(corpus silent)` flag, citation-required `[source: file \| id: 12hex]` (`corpus.py:181`, `composer.py:100`) |
| Single style | **Mix-match with conflict matrix** `conflicts_with`/`compatible_with` (`composer.py:124`, `styles/baselines/*.yaml:65`) |
| Chat | **Table read** — cushions (constraints), pockets (goals), straight vs kick, leave (`table.py:1`) |

```
Corpus (felt) ─┐
               ├──> Composer (weighted + conflict-aware) ──> Prompt (citation-required) ──> Any LLM
Styles (lenses)─┘                                           └─> Bench (20 tasks, prompt + LLM scoring)
                    └─> GraphRAG (graphify-out/graph.json) ─┘
```

---

## What’s Done

### Phase 0 — Foundation (`v0.1.0` · 2026-09-19)

**Goal:** corpus-at-init + composable minds, LLM-agnostic.

- [x] Project scaffold `pyproject.toml:1` (pydantic, pyyaml, typer, rich) + CLI `efren`
- [x] `Corpus` `efren/core/corpus.py:46` — `CorpusSource`, `CorpusConfig`, `Chunk(id, source, text)`, `ingest()`, `_collect_files()` (handles `**/*` glob), `_chunk_text()` sliding window, `prompt_context()` naive.
- [x] `Style` `efren/core/style.py:23` — `Heuristic`, `ReasoningFilter`, `from_yaml/to_yaml`, `prompt_block()`.
- [x] `Mind` `efren/core/mind.py:18` — persisted YAML (`minds/*.yaml`), `render_prompt()`, `from_mix_string()`.
- [x] `Composer` `efren/core/composer.py:17` — `parse_mix("tesla=0.5,efren=0.3")` normalized, `compose_prompt()` merges filters/heuristics/lenses, output protocol Angles→Table→Shot→Execution→Safety.
- [x] `LLM` adapter `efren/core/llm.py:1` — `build_messages()`, `call_openai()`, `dry_run_preview()`.
- [x] Registry `efren/styles/registry.py:12` — loads `baselines/*.yaml` + `~/.efren/styles`.
- [x] 7 baselines: `tesla` Visionary, `edison` Systematizer, `curie` Experimentalist, `einstein` Theorist, `davinci` Polymath, `hopper` Pragmatist, `efren` The Magician (`efren/styles/baselines/efren.yaml:1` — 4 heuristics, 4 filters).
- [x] CLI `efren/cli/main.py:1` — `init --corpus`, `style list/show`, `mind create/list/compose/preview`, `corpus show/ingest`, `chat`.
- [x] `config/*.example.yaml`, `examples/01_quickstart.py`, `examples/02_cli_walkthrough.sh`, `examples/corpus/notes.md` (SODIS/ceramic/carbon), `tests/test_composer.py` (4 tests).
- [x] `.opencode` not yet — plain `~/Downloads/_project/efren` package.

### Phase 0.1 — Honesty + Feel (`v0.1.1` · 2026-09-19)

**Goal:** make the magician honest and tangible. Inspired by self-critique via 3 Efren minds (efren+hopper+curie, einstein+edison+davinci, tesla+davinci+hopper → `/tmp/*_prompt.md`).

- [x] **Corpus search + citation enforcement** (`corpus.py:138`)
  - `search(query, top_k)` keyword TF + phrase bonus + stopword filter (`len>3`, STOP set), ranking.
  - `prompt_context(max_chars, query=task)` now **query-ranked** (was first-N) + `(corpus silent for query ...)` fail-closed.
  - `Mind.render_prompt()` passes `task` as query (`mind.py:34`).
  - `Composer` header upgraded to `CITATION REQUIRED` (`composer.py:100`): must cite `[source: <file> | id: <id>]` or flag `(corpus silent)`, execution & safety cite as well.
  - CLI `corpus search "<query>" --top` (`cli/main.py:311`, `markup=False` fix for `[source:`).

- [x] **Table visualizer** (`table.py:1`)
  - `TableRead(cushions, pockets, balls, straight_shot, magician_shot, leave)`, `analyze_task()` heuristic keyword→cushions/pockets, `render_ascii()` + `render_markdown()`.
  - CLI `efren table "Design ..." --save` (`cli/main.py:334`).

- [x] **Conflict matrix** (`style.py:36`, baselines `*.yaml:65`)
  - `conflicts_with` / `compatible_with` per style (e.g., `tesla: [edison,hopper]`, `efren: []` compatible all).
  - `Composer.detect_conflicts()` + injected `⚠️ Style tension detected` block (`composer.py:62,124`).
  - CLI `mind create` warns on tension, `style show` prints conflicts/compatible (`cli/main.py:142,188`).

- [x] **Opencode skill** (`.opencode/skills/efren/SKILL.md:1`)
  - `/efren` skill: workflow init→list→mix→table→compose, conflict notes, file map.

- [x] Fixes: `**/*` glob top-level match (`corpus.py:96`), YAML quoting for `prompt_fragment: "Ask: ..."`, absolute path resolve in `init` (`cli/main.py:66`).

### Phase 1 — GraphRAG + Bench (`v0.1.2` · 2026-09-19)

**Goal:** replace naive chunks with graph context and prove invention with bench.

- [x] **Graph adapter** `efren/core/graph.py:1`
  - `find_graph()` checks `project/graphify-out`, `cwd`, `~/Downloads/_project/efren`.
  - `query_graph()` shells `graphify query --budget`, fallback to explicit `--graph`.
  - `_build_lightweight_graph()` offline fallback: keyword nodes + file nodes → 13 nodes/12 edges for `examples/corpus` (no LLM key needed).
  - `build_graph(source_path, project_root, mode)` tries `graphify <path>` then fallback on `no LLM API key` error.
  - `graph_context_for_prompt()` tries CLI query, then `fallback_graph_nodes()` keyword scan.
  - `Corpus` now `vector_store: graph` + auto-detect `has_graph()` in `prompt_context()` (`corpus.py:1,23,181`), `graph_status()`.

- [x] **Corpus GraphRAG CLI** (`cli/main.py:338`)
  - `efren corpus graphify --path ./corpus [--mode deep]` → `graphify-out/graph.json`
  - `efren corpus graph-query "How does SODIS work?" --budget 1500`
  - `efren corpus graph-status` (nodes/edges + keyword fallback)

- [x] **Invention Bench** `bench/invention_bench.yaml:1` (20 tasks) + `efren/core/bench.py:1`
  - Tasks: water-lowcost, water-sodis-boost, energy-gravity-light, energy-cookstove, mechanics-egg-drop, mechanics-pulley-lift, mechanics-heat-exchanger, bio-mold-detector, bio-seed-bank, shelter-cool-no-power, shelter-flood-barrier, comm-mesh-offgrid, sensing-water-quality, robotics-line-follower-cheap, food-preservation, waste-plastic-brick, transport-bike-cargo, health-sanitizer, health-wound-dressing, instrument-spectrometer (water/energy/mechanics/bio/shelter/comms/sensing/robotics/food/waste/transport/health/instrument, easy/medium/hard).
  - Rubric: `citation`, `angles`, `table_read`, `execution`, `safety` (prompt heuristic) + expected_citations gold bonus (`bench.py:50,97`).
  - CLI `bench list` / `show --task water-lowcost` / `run magician-default --project --output --top` (`cli/main.py:462`, `bench` typer). Prompt-only scoring, `GraphRAG active` indicator, `by_category`/`by_difficulty` tables. `graphify-out/graph.json` prebuilt at project root (13 nodes).

### Phase 1.1 — LLM Scoring (`v0.1.3` · 2026-09-19)

**Goal:** grade real outputs, not just prompts.

- [x] **LLM adapter mock** (`llm.py:17`)
  - `call_mock(messages, task)` deterministic template that passes all 5 checks (used for `--mock`).
  - `call_llm(messages, mock, model)` unified entry.

- [x] **Bench LLM scoring** (`bench.py:97`)
  - `score_llm_output()` strict (needs `[source: | id:]` or `(corpus silent)`, kick shot, cushions/pockets, steps+falsifi, safety/fail).
  - `score_llm_output_detailed()` + `score_to_float()` + gold citation details.

- [x] **CLI `bench run --llm`** (`cli/main.py:462`)
  - Flags: `--llm` (requires `OPENAI_API_KEY` or `--mock`), `--model gpt-4o-mini`, `--mock`, `--output`, `--top`.
  - Loops 20 tasks: `render_prompt → build_messages → call_llm → score_llm_output_detailed`, 0.3s sleep between real calls, progress `[i/20] prompt X% → llm Y%`, summary `Prompt Score` + `LLM Score` + `By category (LLM)` + worst/best LLM, saves `llm_output[:4000]` per task to JSON (`llm_avg`, `mock`, `model`).
  - Failure modes: `--llm` without key → exit with tip; mock passes 100% by design (real models differentiate on citation discipline).

- [x] Docs: `README.md:132` Phase 1.1 section, skill `SKILL.md:84` (§8 bench --llm), walkthrough updated, reinstall + pytest 4 pass verified, `examples/01_quickstart.py` still passes.

### Phase 1.2 — Unseen Angles (`v0.1.4` · 2026-11-06)

**Goal:** surface corpus combinations a researcher wouldn't reach for — offline take on *The Alien Space of Science* ([arXiv:2603.01092](https://arxiv.org/abs/2603.01092), [repo](https://github.com/alejandrohdez00/alien-space-of-science)). Idea borrowed, no heavy deps (their models are trained on ML papers and need GPUs).

- [x] **`efren/core/angles.py`** — chunks → idea atoms (bullets/lines/paragraphs, cite parent chunk id); rank k=3 triplets by `(1-β)·z(coherence) + β·z(unavailability)`, β=0.7 default.
  - Coherence proxy: atoms must chain (shared stemmed terms, task terms as hub); scored by mean + max task-term overlap.
  - Unavailability proxy: `1 - mean pairwise Jaccard` + source/chunk diversity bonus.
  - Fail-closed: no task anchor → `[]`. Atom reuse capped at 2 across the top list.
- [x] CLI `efren corpus angles "<task>" --top 5 --beta 0.7`; `mind compose/preview --angles N --beta` injects an `## Unseen angles` block (opt-in, default prompt unchanged so bench scores are stable).
- [x] `tests/test_angles.py` (5 tests).
- [ ] Next: swap lexical proxies for embeddings once `vector_store: chroma` lands; bench A/B `--angles 0` vs `--angles 3` with `--llm`.

---

## Architecture Snapshot

```
efren/
├── .opencode/skills/efren/SKILL.md          # /efren
├── bench/invention_bench.yaml               # 20 magician tasks
├── graphify-out/graph.json + GRAPH_REPORT.md# lightweight offline (13/12) or full
├── config/{efren,corpus}.yaml.example
├── efren/__init__.py
├── efren/core/
│   ├── corpus.py    # chunk + search (TF/stop) + prompt_context(query) + graph switch
│   ├── graph.py     # find/query/build + lightweight fallback + graph_context_for_prompt
│   ├── style.py     # Style + conflicts_with/compatible_with
│   ├── composer.py  # normalize/parse_mix/detect_conflicts/compose_prompt/blend_traits
│   ├── mind.py      # Mind YAML + render_prompt(query=task)
│   ├── table.py     # TableRead + analyze/render_ascii/markdown + render_for_task
│   ├── bench.py     # BenchTask/Config + score_prompt/llm_output_detailed/summarize
│   └── llm.py       # build_messages/call_openai/call_mock/call_llm/dry_run_preview
├── efren/styles/baselines/*.yaml           # 7 lenses, each with heuristics/filters/conflicts
│   ├── tesla.yaml [edison,hopper] / [einstein,efren]
│   ├── edison.yaml [tesla,einstein] / [curie,hopper]
│   ├── curie.yaml [tesla,davinci] / [edison,efren]
│   ├── einstein.yaml [edison,hopper] / [tesla,davinci]
│   ├── davinci.yaml [curie,hopper] / [einstein,efren,tesla]
│   ├── hopper.yaml [tesla,einstein,davinci] / [edison,efren]
│   └── efren.yaml [] / all
├── efren/styles/registry.py                # loads baselines + ~/.efren/styles
├── efren/cli/main.py                       # typer: init, style, mind, corpus, table, bench, chat
├── examples/{01_quickstart.py,02_cli_walkthrough.sh,corpus/notes.md}
└── tests/test_composer.py
```

CLI map: `efren init`, `style list/show`, `mind create/list/compose/preview`, `corpus show/ingest/search/graphify/graph-query/graph-status`, `table`, `bench list/run/show`, `chat` (`--help` per group).

---

## How to Use (30s → 5 min)

```bash
pip install -e ~/Downloads/_project/efren --break-system-packages -q

# 1. felt
efren init ./my_lab --corpus ./papers --name my_lab

# 2. read table before shooting
efren table "Design heat exchanger from scrap"

# 3. mix magicians (tension warned)
efren mind create magician-alpha --mix efren=0.4,tesla=0.3,curie=0.3

# 4. search + graph
efren corpus search "SODIS" --project ./my_lab
efren corpus graphify --path ./corpus --project ./my_lab   # lightweight if no key
efren corpus graph-query "How does SODIS work?" --project ./my_lab

# 5. render (citation-required, GraphRAG if present)
efren mind preview magician-alpha --task "Design water purifier" --project ./my_lab
efren mind compose magician-alpha --task "Design water purifier" --project ./my_lab --save /tmp/prompt.md

# 6. bench
efren bench list
efren bench run magician-alpha --project ./my_lab                      # prompt-only
efren bench run magician-alpha --project ./my_lab --llm --mock          # mock LLM, no key
efren bench run magician-alpha --project ./my_lab --llm --model gpt-4o # needs OPENAI_API_KEY
```

Python: `examples/01_quickstart.py` — `Corpus.search`, `render_for_task`, `Mind.from_mix_string`, `bench.load_bench`.

Opencode: `/efren` in any session → skill auto-loads.

---

## What’s Next — If Anything

Nothing is *required* — Efren is shippable today as prompt-only + mock bench. Below is a prioritized backlog if you want to keep playing. Ordered by effort/impact and Efren differentiation.

### Next (small, high leverage — 1–2 days total)

- [ ] **Bench compare mode** `efren bench compare magician-default edison-pure --project --llm --mock` — side-by-side table + winner per category. Makes differentiation visible (currently need two manual runs).
- [ ] **Duel / Rack** `efren duel mindA vs mindB --task "..." --judge` — two minds produce kick shots, third judges on rubric. Adversarial rack, not sequential tasks. Reuse `composer.py:108` output protocol + `bench.py` scoring as judge.
- [ ] **Style learning** `efren style learn ./papers --name my-style` — auto-extract heuristics/filters from corpus (LLM) → `~/.efren/styles/my-style.yaml`. Lowers barrier to custom lenses beyond hand-writing YAML.
- [ ] **MCP server** — expose `efren` as MCP tools (`style_list`, `mind_compose`, `corpus_search`, `table`, `bench_run`) for Claude/opencode. Skill already exists; MCP makes it callable.
- [ ] **Web playground** (Vite + `pyodide` or tiny FastAPI) — sliders for mix weights, live table preview, prompt → paste to LLM. 1-page demo for sharing.

### Soon (medium — 1 week)

- [ ] **Vector store real** — `vector_store: chroma` with `sentence-transformers/all-MiniLM-L6-v2` in `corpus.py:181` + `pip install 'efren[embeddings]'`. Currently keyword TF + lightweight graph; embeddings would beat both.
- [ ] **Graphify deep mode** — wire `GEMINI_API_KEY` path fully (currently lightweight fallback dominates). Add `efren corpus graphify --mode deep --graphify-args "--model ..."` and community labels. Requires setting key.
- [ ] **Eval harness hardening** — current prompt-only scoring is 100% for all minds (composer guarantees). Add mind-specific rubric (e.g., curie-heavy → must mention measurement uncertainty, tesla-heavy → must mention field) + expected_citations strict scoring for LLM.
- [ ] **Corpus provenance UI** — `efren corpus provenance` shows chunk→citation→graph node lineage, `graphify-out/.graphify_analysis.json` god nodes/surprises in CLI.

### Later (if you want Efren to be a platform)

- [ ] **Fine-tuning / PERSONA vectors** — export weighted styles as BILLY-style `v_merged = avg(v_i)` steering vectors for open-weight models (requires model weight access). Efren stays prompt-portable for closed APIs.
- [ ] **Workflow / Agentic** — `efren flow` YAML for multi-step invention (research→table→compose→bench→iterate).
- [ ] **TUI** — `textual` app: `efren tui` shows pool table ASCII + sliders + live prompt.
- [ ] **Publish** — `pip publish` + `uv tool install efren`, Homebrew, Docker.

### Ideated but Parked (intentionally not done — scope control)

- Multi-agent CrewAI/AutoGen export — Efren composes *inside one mind*, not orgs (see roadmap discussion vs `hersona`/`PERSONA`/`BILLY`).
- Competing with embeddings providers — stay LLM-agnostic, let user bring `chromadb`/`openai`.
- Billing/metering — not needed for local suite.

---

## Differentiation — Why Efren vs Similar Projects

| Project | Type | Efren edge |
|---|---|---|
| **hersona** (346 attributes) | persona blend | inventor heuristics + reasoning filters + table protocol, not anime/speech |
| **PERSONA / BILLY** (activation vectors) | vector steering | prompt-portable (closed APIs), plus corpus-at-init + conflict matrix + bench |
| **PersonaFuse MoE** (10 experts) | fine-tuned MoE | zero-training, lightweight fallback graph |
| **CrewAI/AutoGen/PraisonAI** | multi-agent orgs | one consolidated mind (kick shot), not sequential crews |
| **Cognitive Prompting / MeLA** | modular COPs | inventor-specific + billiards output protocol + bench |

If you do only one next thing, do **bench compare + duel** — it turns Efren from “renders prompts” into “proves which mind wins on your table”.

---

## Running

```bash
pip install -e . --break-system-packages
pytest -q  # 4 pass
python examples/01_quickstart.py
bash examples/02_cli_walkthrough.sh  # includes table, search, conflict, graph, bench
```

Versioning: `v0.1.3` current. Tag next as `v0.2.0` after compare/duel.

License: MIT. Feedback: https://github.com/anomalyco/opencode (mention Muse Spark).
