"""Efren CLI — `efren` command."""

from __future__ import annotations

import pathlib
import sys
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

from efren.core.corpus import Corpus, CorpusConfig, CorpusSource
from efren.core.mind import Mind
from efren.core.composer import Composer
from efren.core.table import render_for_task, analyze_task
from efren.core.llm import build_messages, dry_run_preview
from efren.core.bench import load_bench, score_prompt
from efren.core.angles import sample_angles
from efren.core.graph import build_graph, query_graph, has_graph, graph_info
from efren.styles.registry import load_registry

app = typer.Typer(
    name="efren",
    help="Efren — The Magician: composable inventor-mind suite. Mix-match minds + corpus grounding.",
    add_completion=False,
)
console = Console()

# repo checkout root (holds bench/, graphify-out/) when installed editable
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

corpus_app = typer.Typer(help="Corpus commands (corpus is set at init)")
mind_app = typer.Typer(help="Mind commands (compose & render)")
style_app = typer.Typer(help="Style commands")
bench_app = typer.Typer(help="Invention Bench — 20 magician tasks")

app.add_typer(corpus_app, name="corpus")
app.add_typer(mind_app, name="mind")
app.add_typer(style_app, name="style")
app.add_typer(bench_app, name="bench")


def _project_root(explicit: Optional[str] = None) -> pathlib.Path:
    if explicit:
        return pathlib.Path(explicit).resolve()
    # walk up from cwd looking for efren.yaml or corpus.yaml
    cur = pathlib.Path.cwd()
    for p in [cur] + list(cur.parents):
        if (p / "efren.yaml").exists() or (p / "corpus.yaml").exists():
            return p
    return cur


def _load_registry():
    return load_registry()


@app.command()
def init(
    path: str = typer.Argument(".", help="Project path to init"),
    corpus: Optional[str] = typer.Option(None, "--corpus", "-c", help="Corpus source path (file or directory). Can be repeated? Use comma-separated."),
    name: str = typer.Option("efren-project", "--name", "-n", help="Project name"),
    description: str = typer.Option("", "--desc", help="Project description"),
):
    """Init a new efren project. Corpus is SET AT INIT (but you can re-init or edit corpus.yaml)."""
    root = pathlib.Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)

    efren_cfg = root / "efren.yaml"
    corpus_cfg_path = root / "corpus.yaml"

    # build corpus config - resolve relative paths to absolute at init time
    sources = []
    if corpus:
        for c in corpus.split(","):
            c = c.strip()
            if c:
                # resolve to absolute so project remains portable if corpus is elsewhere
                p = pathlib.Path(c)
                if not p.is_absolute():
                    # try resolving relative to cwd, fallback to root
                    abs_p = (pathlib.Path.cwd() / p).resolve()
                    if abs_p.exists():
                        c = str(abs_p)
                    else:
                        # keep as relative to project root - will resolve at ingest
                        c = str(p)
                else:
                    c = str(p)
                sources.append(CorpusSource(path=c))

    corpus_cfg = CorpusConfig(
        name=f"{name}-corpus",
        description=f"Corpus for {name}",
        sources=sources,
    )
    corpus_cfg.to_yaml(corpus_cfg_path)

    # main config
    main_cfg = {
        "project": {"name": name, "description": description or "Efren magician project", "version": "0.1.0"},
        "corpus": {"config": "corpus.yaml"},
        "minds_dir": "minds",
        "styles": {"baselines": "efren/styles/baselines", "user": "~/.efren/styles"},
    }
    efren_cfg.write_text(yaml.safe_dump(main_cfg, sort_keys=False))

    # minds dir
    (root / "minds").mkdir(exist_ok=True)
    # example mind
    example_mind = Mind.from_mix_string(
        name="magician-default",
        mix="efren=0.4,tesla=0.3,curie=0.3",
        registry=_load_registry(),
        description="Default magician mind — creative angles + visual simulation + precision",
    )
    example_mind.save(root / "minds" / "magician-default.yaml")

    console.print(f"[green]Initialized efren project at[/green] {root}")
    console.print(f"  corpus: {corpus_cfg_path} ({len(sources)} sources)")
    console.print(f"  config: {efren_cfg}")
    console.print(f"  minds:  {root / 'minds'}/magician-default.yaml")
    console.print("\nNext: [bold]efren style list[/bold] → [bold]efren mind create --mix tesla=0.5,efren=0.5[/bold] → [bold]efren mind preview magician-default --task '...'\n")


@app.command("styles")
def styles_alias():
    """Alias for `efren style list`."""
    style_list()


@style_app.command("list")
def style_list():
    """List available inventor styles (baselines)."""
    reg = _load_registry()
    table = Table(title="Efren — Baseline Inventor Styles (mix-match these)")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Nickname", style="magenta")
    table.add_column("Summary", style="dim")
    for sid, s in sorted(reg.items()):
        table.add_row(sid, s.display_name, s.nickname or "", s.summary[:90])
    console.print(table)
    console.print("\nMix them: [bold]efren mind create my-mind --mix tesla=0.4,efren=0.4,curie=0.2[/bold]")


@style_app.command("show")
def style_show(style_id: str = typer.Argument(..., help="Style ID e.g., tesla, efren, curie")):
    """Show detail for one style."""
    reg = _load_registry()
    if style_id not in reg:
        console.print(f"[red]Unknown style '{style_id}'[/red]. Available: {', '.join(sorted(reg))}")
        raise typer.Exit(1)
    s = reg[style_id]
    console.print(Markdown(f"# {s.display_name} — *{s.nickname}*"))
    console.print(f"[dim]{s.summary}[/dim]\n")
    console.print(Markdown(s.system_preamble))
    console.print("\n[bold]Heuristics:[/bold]")
    for h in s.heuristics:
        console.print(f"  • [cyan]{h.name}[/cyan]: {h.description}")
        console.print(f"    -> {h.prompt_fragment}")
    console.print("\n[bold]Reasoning filters:[/bold]")
    for i, f in enumerate(s.reasoning_filters, 1):
        console.print(f"  {i}. {f.step}: [italic]{f.question}[/italic]")
    if s.conflicts_with:
        console.print("\n[bold yellow]Conflicts with:[/bold yellow]", ", ".join(s.conflicts_with))
    if s.compatible_with:
        console.print("[bold green]Compatible with:[/bold green]", ", ".join(s.compatible_with))


@mind_app.command("list")
def mind_list(project: Optional[str] = typer.Option(None, "--project", help="Project root")):
    """List minds in project."""
    root = _project_root(project)
    minds_dir = root / "minds"
    if not minds_dir.exists():
        console.print(f"[yellow]No minds dir at {minds_dir} — run `efren init` first[/yellow]")
        raise typer.Exit(0)
    table = Table(title=f"Minds in {root}")
    table.add_column("Name", style="cyan")
    table.add_column("Composition", style="green")
    table.add_column("Description", style="dim")
    for p in sorted(minds_dir.glob("*.yaml")):
        try:
            m = Mind.load(p)
            comp = ", ".join(f"{w.style_id}={w.weight:.2f}" for w in m.composition)
            table.add_row(m.name, comp, m.description[:60])
        except Exception as e:
            table.add_row(p.stem, f"[red]error: {e}[/red]", "")
    console.print(table)


@mind_app.command("create")
def mind_create(
    name: str = typer.Argument(..., help="Mind name e.g., my-magician"),
    mix: str = typer.Option(..., "--mix", "-m", help="Mix e.g., 'tesla=0.5,efren=0.3,curie=0.2' or 'tesla,curie'"),
    description: str = typer.Option("", "--desc", help="Description"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """Create a new composable mind (mix-match styles)."""
    root = _project_root(project)
    reg = _load_registry()
    try:
        mind = Mind.from_mix_string(name=name, mix=mix, registry=reg, description=description)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    # conflict check (hersona-style)
    from efren.core.composer import Composer

    composer = Composer(reg)
    conflicts = composer.detect_conflicts(mind.composition)
    if conflicts:
        console.print("[yellow]⚠️  Style tension detected:[/yellow]")
        for c in conflicts:
            console.print(f"  • {c}")
        console.print("[dim]Prompt will include tension note — reconcile or pick primary lens.[/dim]")
    minds_dir = root / "minds"
    minds_dir.mkdir(parents=True, exist_ok=True)
    out = minds_dir / f"{name}.yaml"
    if out.exists():
        console.print(f"[red]Mind already exists: {out}[/red] — use `efren mind compose` to update or remove it first")
        raise typer.Exit(1)
    mind.save(out)
    console.print(f"[green]Created mind '{name}'[/green] at {out}")
    console.print(f"  mix: {mix} → normalized: {', '.join(f'{w.style_id}={w.weight:.2f}' for w in mind.composition)}")
    console.print(f"  preview: [bold]efren mind preview {name} --task 'Design a ...'[/bold]")
    console.print(f"  table:   [bold]efren table --task '...'[/bold] to see cushions/pockets first")


@mind_app.command("compose")
def mind_compose(
    name: str = typer.Argument(..., help="Mind name to compose/render"),
    task: str = typer.Option(..., "--task", "-t", help="Task/problem to render prompt for"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
    save_prompt: Optional[str] = typer.Option(None, "--save", help="Save rendered prompt to file"),
    angles: int = typer.Option(0, "--angles", "-a", help="Inject N unseen corpus angles (0 = off)"),
    beta: float = typer.Option(0.7, "--beta", help="Angles: weight on unavailability vs coherence (0..1)"),
):
    """Render the consolidated system prompt for a mind + task (corpus-grounded)."""
    root = _project_root(project)
    reg = _load_registry()
    mind_path = root / "minds" / f"{name}.yaml"
    if not mind_path.exists():
        # also try direct path
        p2 = pathlib.Path(name)
        if p2.exists():
            mind_path = p2
        else:
            console.print(f"[red]Mind not found: {mind_path}[/red]")
            console.print(f"Available: {', '.join(p.stem for p in (root/'minds').glob('*.yaml')) if (root/'minds').exists() else '(none)'}")
            raise typer.Exit(1)
    mind = Mind.load(mind_path)
    corpus = Corpus.load(root)
    prompt = mind.render_prompt(registry=reg, corpus=corpus, task=task, angles=angles, beta=beta)
    if save_prompt:
        pathlib.Path(save_prompt).write_text(prompt)
        console.print(f"[green]Saved prompt to {save_prompt} ({len(prompt)} chars)[/green]")
    else:
        console.print(Markdown(f"## Efren Mind: {mind.name}\n"))
        # Use pager-like print but truncated for terminal
        console.print(prompt[:12000])
        if len(prompt) > 12000:
            console.print(f"\n[dim]... truncated {len(prompt)-12000} chars — use --save to get full prompt[/dim]")


@mind_app.command("preview")
def mind_preview(
    name: str = typer.Argument(..., help="Mind name"),
    task: str = typer.Option("Design a novel solution to a hard problem in your domain", "--task", "-t"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
    angles: int = typer.Option(0, "--angles", "-a", help="Inject N unseen corpus angles (0 = off)"),
    beta: float = typer.Option(0.7, "--beta", help="Angles: weight on unavailability vs coherence (0..1)"),
):
    """Dry-run preview: show system prompt + user task as LLM messages (no API call)."""
    root = _project_root(project)
    reg = _load_registry()
    mind_path = root / "minds" / f"{name}.yaml"
    if not mind_path.exists():
        console.print(f"[red]Mind not found: {mind_path}[/red]")
        raise typer.Exit(1)
    mind = Mind.load(mind_path)
    corpus = Corpus.load(root)
    system_prompt = mind.render_prompt(registry=reg, corpus=corpus, task=task, angles=angles, beta=beta)
    preview = dry_run_preview(system_prompt, task)
    console.print(preview[:8000])
    # also show messages shape
    msgs = build_messages(system_prompt, task)
    console.print(f"\n[dim]Messages: {len(msgs)} | system: {len(msgs[0]['content'])} chars | ready for any OpenAI-compatible LLM[/dim]")


@corpus_app.command("show")
def corpus_show(project: Optional[str] = typer.Option(None, "--project", help="Project root")):
    """Show corpus config and ingested chunk count."""
    root = _project_root(project)
    corpus = Corpus.load(root)
    console.print(f"[bold]Corpus:[/bold] {corpus.config.name}")
    console.print(f"  description: {corpus.config.description}")
    console.print(f"  sources: {len(corpus.config.sources)}")
    for s in corpus.config.sources:
        console.print(f"    - {s.path} ({s.kind}) glob={s.include_glob}")
    chunks = corpus.ingest()
    console.print(f"  chunks: {len(chunks)} (chunk_size={corpus.config.chunk_size})")
    if chunks:
        console.print(f"  preview chars: {len(corpus.prompt_context())}")
        console.print("[dim]Tip: efren corpus search \"query\" for citation-ranked hits[/dim]")


@corpus_app.command("ingest")
def corpus_ingest(project: Optional[str] = typer.Option(None, "--project", help="Project root")):
    """Ingest corpus and report stats."""
    root = _project_root(project)
    corpus = Corpus.load(root)
    chunks = corpus.ingest()
    console.print(f"[green]Ingested {len(chunks)} chunks[/green] from {len(corpus.config.sources)} sources")
    for c in chunks[:5]:
        console.print(f"  [dim]{c.id}[/dim] {c.source} — {c.text[:100].replace(chr(10), ' ')}...")


@corpus_app.command("search")
def corpus_search(
    query: str = typer.Argument(..., help="Keyword query"),
    top_k: int = typer.Option(5, "--top", "-k", help="Top K hits"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """Keyword search corpus (citation ids) — lightweight, no embeddings."""
    root = _project_root(project)
    corpus = Corpus.load(root)
    hits = corpus.search(query, top_k=top_k)
    if not hits:
        console.print(f"[yellow]No hits for '{query}' — corpus silent. Try broader terms or efren corpus show[/yellow]")
        console.print(f"[dim]Prompt will render '(corpus silent — reasoning from first principles)'[/dim]")
        return
    console.print(f"[green]Top {len(hits)} hits for '{query}':[/green]")
    for h in hits:
        # use markup=False to avoid Rich stripping [source: ...] brackets
        console.print(f"[source: {pathlib.Path(h.source).name} | id: {h.id}]  {h.source}", style="cyan", markup=False)
        snippet = h.text[:300].replace("\n", " ")
        console.print(f"  {snippet}...", markup=False)
    console.print("Cite as [source: <file> | id: <id>] in your output.", style="dim", markup=False)


@corpus_app.command("angles")
def corpus_angles(
    task: str = typer.Argument(..., help="Task to find unseen angles for"),
    top_k: int = typer.Option(5, "--top", "-k", help="Top K combinations"),
    beta: float = typer.Option(0.7, "--beta", help="Weight on unavailability vs coherence (0..1)"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """Sample coherent-but-unavailable idea triplets from the corpus (alien-space style, offline)."""
    root = _project_root(project)
    corpus = Corpus.load(root)
    try:
        angles = sample_angles(corpus, task, top_k=top_k, beta=beta)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    if not angles:
        console.print(f"[yellow]No angles for '{task}' — corpus silent for the task, or too sparse to chain 3 related ideas[/yellow]")
        return
    console.print(f"[green]Top {len(angles)} unseen angles (beta={beta}):[/green]")
    for i, a in enumerate(angles, 1):
        console.print(a.render(i), markup=False, soft_wrap=True)
    console.print("Use in a prompt: efren mind compose <mind> --task ... --angles 3", style="dim", markup=False)


@corpus_app.command("graphify")
def corpus_graphify(
    path: Optional[str] = typer.Option(None, "--path", help="Corpus path to graphify (defaults to first source in corpus.yaml)"),
    mode: str = typer.Option("", "--mode", help="Graphify mode: deep or empty"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """Build graphify graph from corpus sources (enables GraphRAG)."""
    root = _project_root(project)
    # resolve source path
    if path:
        src = pathlib.Path(path)
    else:
        corpus = Corpus.load(root)
        if not corpus.config.sources:
            console.print("[red]No corpus sources — add to corpus.yaml or use efren init --corpus[/red]")
            raise typer.Exit(1)
        # use first source
        first = corpus.config.sources[0].path
        src = pathlib.Path(first)
        if not src.is_absolute():
            src = (root / src).resolve()
    console.print(f"[dim]Building graphify graph from {src} (mode={mode or 'quick'})...[/dim]")
    res = build_graph(src, root, mode=mode)
    if res.get("ok"):
        console.print("[green]Graph built: graphify-out/graph.json[/green]")
        console.print(res.get("stdout", "")[-1500:])
        info = graph_info(root)
        if info:
            console.print(f"  nodes: {info['nodes']}, edges: {info['edges']}")
    else:
        console.print(f"[red]Graph build failed: {res.get('error') or res.get('stderr')}[/red]")
        raise typer.Exit(1)


@corpus_app.command("graph-query")
def corpus_graph_query(
    question: str = typer.Argument(..., help="Question to query the graph"),
    budget: int = typer.Option(1500, "--budget", help="Token budget"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """Query the graphify graph (BFS) — GraphRAG."""
    root = _project_root(project)
    if not has_graph(root):
        console.print("[yellow]No graph found at graphify-out/graph.json — run `efren corpus graphify` first[/yellow]")
        raise typer.Exit(1)
    console.print(f"[dim]Querying graph: {question} (budget {budget})...[/dim]")
    out = query_graph(question, root, budget=budget)
    if not out:
        console.print("[yellow]No result from graphify query — try broader question or check graphify install[/yellow]")
        raise typer.Exit(1)
    console.print(Markdown(out[:12000]))
    if len(out) > 12000:
        console.print(f"\n[dim]... truncated {len(out)-12000} chars[/dim]")


@corpus_app.command("graph-status")
def corpus_graph_status(project: Optional[str] = typer.Option(None, "--project", help="Project root")):
    """Show graphify graph status (nodes/edges)."""
    root = _project_root(project)
    info = graph_info(root)
    if not info:
        console.print("[yellow]No graph at graphify-out/graph.json[/yellow]")
        console.print("Run `efren corpus graphify --path <corpus>` to build it.")
        return
    console.print(f"[green]Graph:[/green] {info['path']}")
    console.print(f"  nodes: {info['nodes']}, edges: {info['edges']}, directed: {info.get('directed')}")
    # also show keyword fallback status
    corpus = Corpus.load(root)
    chunks = corpus.ingest()
    console.print(f"[dim]Keyword corpus chunks: {len(chunks)} | vector_store: {corpus.config.vector_store}[/dim]")
    if corpus.config.vector_store == "graph" and not has_graph(root):
        console.print("[yellow]vector_store=graph but no graph.json — run graphify first, or set to none[/yellow]")


@app.command()
def table(
    task: Optional[str] = typer.Argument(None, help="Task/problem to read as a billiards table"),
    task_opt: Optional[str] = typer.Option(None, "--task", "-t", help="Task (alternative to positional)"),
    save: Optional[str] = typer.Option(None, "--save", help="Save table markdown to file"),
):
    """Render the billiards table — cushions, pockets, straight vs magician shot."""
    t = task_opt or task
    if not t:
        console.print("[red]Provide a task: efren table \"Design ...\" or efren table --task \"Design ...\"[/red]")
        raise typer.Exit(1)
    md = render_for_task(t)
    if save:
        pathlib.Path(save).write_text(md)
        console.print(f"[green]Saved table to {save}[/green]")
    else:
        console.print(Markdown(md))


# ── Bench commands ──────────────────────────────────────────────────────────


@bench_app.command("list")
def bench_list(
    bench: str = typer.Option("bench/invention_bench.yaml", "--bench", help="Bench YAML path"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """List bench tasks."""
    root = _project_root(project)
    bpath = pathlib.Path(bench)
    if not bpath.is_absolute():
        bpath = _REPO_ROOT / bpath
        if not bpath.exists():
            bpath = root / bench
    if not bpath.exists():
        console.print(f"[red]Bench not found: {bpath}[/red]")
        raise typer.Exit(1)
    cfg = load_bench(bpath)
    bench_name = cfg.bench.get("name", bpath.stem)
    console.print(f"[bold]Bench: {bench_name}[/bold] — {len(cfg.tasks)} tasks")
    t = Table(title=bench_name)
    t.add_column("ID", style="cyan", no_wrap=True)
    t.add_column("Category", style="magenta")
    t.add_column("Diff", style="yellow")
    t.add_column("Task", style="dim")
    for task in cfg.tasks:
        t.add_row(task.id, task.category, task.difficulty, task.task[:70])
    console.print(t)


@bench_app.command("run")
def bench_run(
    mind: str = typer.Argument(..., help="Mind name to evaluate"),
    bench: str = typer.Option("bench/invention_bench.yaml", "--bench", help="Bench YAML"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save JSON results"),
    top: int = typer.Option(5, "--top", help="Show top N tasks detail"),
    llm: bool = typer.Option(False, "--llm", help="Call LLM and score outputs (requires OPENAI_API_KEY or --mock)"),
    model: str = typer.Option("gpt-4o-mini", "--model", help="LLM model for --llm"),
    mock: bool = typer.Option(False, "--mock", help="Use deterministic mock LLM (no API key, for CI/demo)"),
    angles: int = typer.Option(0, "--angles", "-a", help="Inject N unseen corpus angles per task (0 = off)"),
    beta: float = typer.Option(0.7, "--beta", help="Angles: weight on unavailability vs coherence (0..1)"),
):
    """Run invention bench — prompt-only by default; add --llm to score real LLM outputs."""
    import json as _json
    import os
    import time

    root = _project_root(project)
    reg = _load_registry()
    # resolve mind
    mind_path = root / "minds" / f"{mind}.yaml"
    if not mind_path.exists():
        p2 = pathlib.Path(mind)
        if p2.exists():
            mind_path = p2
        else:
            console.print(f"[red]Mind not found: {mind_path}[/red]")
            raise typer.Exit(1)
    m = Mind.load(mind_path)
    corpus = Corpus.load(root)

    # resolve bench
    bpath = pathlib.Path(bench)
    if not bpath.is_absolute():
        cand1 = _REPO_ROOT / bench
        cand2 = root / bench
        if cand1.exists():
            bpath = cand1
        elif cand2.exists():
            bpath = cand2
    if not bpath.exists():
        console.print(f"[red]Bench not found: {bpath}[/red]")
        raise typer.Exit(1)
    cfg = load_bench(bpath)

    mode = "LLM" if llm else "prompt-only"
    console.print(f"[dim]Bench: {cfg.bench.get('name')} — {len(cfg.tasks)} tasks | mind: {mind} ({', '.join(f'{w.style_id}={w.weight:.2f}' for w in m.composition)}) | mode: {mode} | angles: {angles}[/dim]")

    from efren.core.bench import summarize, score_llm_output_detailed, score_to_float

    if llm and not mock and not os.getenv("OPENAI_API_KEY"):
        console.print("[red]--llm requires OPENAI_API_KEY or --mock[/red]")
        console.print("Try: efren bench run magician-default --llm --mock  (no key, deterministic)")
        raise typer.Exit(1)

    scores = []
    llm_scores = []
    results = []

    for idx, task in enumerate(cfg.tasks, 1):
        prompt = m.render_prompt(registry=reg, corpus=corpus, task=task.task, angles=angles, beta=beta)
        sc = score_prompt(prompt, task, corpus_available=len(corpus.ingest()) > 0)
        scores.append(sc)

        entry: dict = {
            "task_id": task.id,
            "category": task.category,
            "difficulty": task.difficulty,
            "prompt_score": sc.score,
            "prompt_checks": sc.checks,
            "prompt_details": sc.details,
            "prompt_len": sc.prompt_len,
            "angles_injected": "## Unseen angles" in prompt,
        }

        if llm:
            from efren.core.llm import build_messages, call_llm

            messages = build_messages(prompt, task.task)
            try:
                out = call_llm(messages, model=model, mock=mock, task=task.task)
            except Exception as e:
                console.print(f"[red]LLM call failed on {task.id}: {e}[/red]")
                entry["llm_error"] = str(e)
                out = ""
            checks, details = score_llm_output_detailed(out, task)
            entry["llm_checks"] = checks
            entry["llm_details"] = details
            entry["llm_score"] = score_to_float(checks)
            entry["llm_output"] = out[:4000]  # truncated for JSON
            llm_scores.append(entry["llm_score"])
            # small sleep to avoid rate limit
            if not mock and idx < len(cfg.tasks):
                time.sleep(0.3)
            # progress
            console.print(f"  [{idx}/{len(cfg.tasks)}] {task.id} prompt {sc.score:.0%} → llm {entry['llm_score']:.0%} {'✓' if entry['llm_score'] >= 0.8 else '·'}")
        else:
            entry["score"] = sc.score
            entry["checks"] = sc.checks
            entry["details"] = sc.details

        results.append(entry)

    # prompt summary
    summary = summarize(scores)
    console.print(f"\n[bold]Prompt Score: {summary['avg']:.2%} avg over {summary['count']} tasks[/bold]")
    cat_table = Table(title="By category (prompt)")
    cat_table.add_column("Category", style="cyan")
    cat_table.add_column("Avg", style="green")
    for cat, avg in sorted(summary["by_category"].items()):
        cat_table.add_row(cat, f"{avg:.0%}")
    console.print(cat_table)
    diff_table = Table(title="By difficulty (prompt)")
    diff_table.add_column("Difficulty", style="yellow")
    diff_table.add_column("Avg", style="green")
    for diff, avg in sorted(summary["by_difficulty"].items()):
        diff_table.add_row(diff, f"{avg:.0%}")
    console.print(diff_table)

    if llm and llm_scores:
        avg_llm = sum(llm_scores) / len(llm_scores) if llm_scores else 0
        console.print(f"\n[bold]LLM Score: {avg_llm:.2%} avg over {len(llm_scores)} tasks (mock={mock}, model={model})[/bold]")
        # llm by category
        from collections import defaultdict

        by_cat_llm: Dict[str, list] = defaultdict(list)
        by_diff_llm: Dict[str, list] = defaultdict(list)
        for r in results:
            if "llm_score" in r:
                by_cat_llm[r["category"]].append(r["llm_score"])
                by_diff_llm[r["difficulty"]].append(r["llm_score"])
        cat_llm_table = Table(title="By category (LLM)")
        cat_llm_table.add_column("Category", style="cyan")
        cat_llm_table.add_column("Avg LLM", style="green")
        for cat, vals in sorted(by_cat_llm.items()):
            cat_llm_table.add_row(cat, f"{sum(vals)/len(vals):.0%}")
        console.print(cat_llm_table)
        diff_llm_table = Table(title="By difficulty (LLM)")
        diff_llm_table.add_column("Difficulty", style="yellow")
        diff_llm_table.add_column("Avg LLM", style="green")
        for diff, vals in sorted(by_diff_llm.items()):
            diff_llm_table.add_row(diff, f"{sum(vals)/len(vals):.0%}")
        console.print(diff_llm_table)

    # top detail (prompt)
    scores_sorted = sorted(scores, key=lambda s: s.score)
    console.print(f"\n[dim]Worst {top} tasks (prompt):[/dim]")
    for sc in scores_sorted[:top]:
        checks = ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in sc.checks.items())
        console.print(f"  [cyan]{sc.task_id}[/cyan] {sc.score:.0%} — {checks}")

    console.print(f"\n[dim]Best {top} tasks (prompt):[/dim]")
    for sc in sorted(scores, key=lambda s: s.score, reverse=True)[:top]:
        checks = ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in sc.checks.items())
        console.print(f"  [cyan]{sc.task_id}[/cyan] {sc.score:.0%} — {checks}")

    if llm and results and any("llm_score" in r for r in results):
        # worst/best llm
        llm_sorted = sorted([r for r in results if "llm_score" in r], key=lambda r: r["llm_score"])
        console.print(f"\n[dim]Worst {top} tasks (LLM):[/dim]")
        for r in llm_sorted[:top]:
            c = ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in r["llm_checks"].items())
            console.print(f"  [cyan]{r['task_id']}[/cyan] {r['llm_score']:.0%} — {c}")
        console.print(f"\n[dim]Best {top} tasks (LLM):[/dim]")
        for r in sorted([r for r in results if "llm_score" in r], key=lambda r: r["llm_score"], reverse=True)[:top]:
            c = ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in r["llm_checks"].items())
            console.print(f"  [cyan]{r['task_id']}[/cyan] {r['llm_score']:.0%} — {c}")

    if output:
        out_path = pathlib.Path(output)
        out_path.write_text(_json.dumps({"mind": mind, "bench": str(bpath), "mode": mode, "mock": mock, "model": model, "angles": angles, "beta": beta, "summary": summary, "llm_avg": sum(llm_scores)/len(llm_scores) if llm_scores else None, "results": results}, indent=2))
        console.print(f"\n[green]Saved results to {out_path}[/green]")

    # hint about graph
    if has_graph(root):
        console.print("[dim]GraphRAG active (graphify-out/graph.json found) — prompts were graph-grounded[/dim]")
    else:
        console.print("[dim]Tip: efren corpus graphify --path ./corpus to enable GraphRAG (better than keyword)[/dim]")


@bench_app.command("show")
def bench_show(
    bench: str = typer.Argument("bench/invention_bench.yaml", help="Bench YAML"),
    task_id: Optional[str] = typer.Option(None, "--task", help="Show single task"),
):
    """Show bench tasks detail."""
    bpath = pathlib.Path(bench)
    if not bpath.is_absolute():
        cand = _REPO_ROOT / bench
        if cand.exists():
            bpath = cand
    if not bpath.exists():
        console.print(f"[red]Bench not found: {bpath}[/red]")
        raise typer.Exit(1)
    cfg = load_bench(bpath)
    if task_id:
        for t in cfg.tasks:
            if t.id == task_id:
                console.print(Markdown(f"## {t.id} — {t.category} / {t.difficulty}\n\n{t.task}\n\n**Constraints:** {', '.join(t.constraints)}\n\n**Expected citations:** {', '.join(t.expected_citations) or '(none)'}"))
                return
        console.print(f"[red]Task {task_id} not found[/red]")
        raise typer.Exit(1)
    for t in cfg.tasks:
        console.print(f"[cyan]{t.id:22}[/cyan] {t.difficulty:6} {t.category:10} {t.task[:60]}")


@app.command()
def chat(
    mind: str = typer.Argument(..., help="Mind name"),
    task: str = typer.Option(..., "--task", "-t", help="User task"),
    model: str = typer.Option("gpt-4o-mini", "--model", help="OpenAI model"),
    project: Optional[str] = typer.Option(None, "--project", help="Project root"),
):
    """Call an OpenAI-compatible LLM with the composed mind (requires OPENAI_API_KEY)."""
    from efren.core.llm import call_openai

    root = _project_root(project)
    reg = _load_registry()
    mind_path = root / "minds" / f"{mind}.yaml"
    if not mind_path.exists():
        console.print(f"[red]Mind not found: {mind_path}[/red]")
        raise typer.Exit(1)
    m = Mind.load(mind_path)
    corpus = Corpus.load(root)
    system_prompt = m.render_prompt(registry=reg, corpus=corpus, task=task)
    messages = build_messages(system_prompt, task)
    console.print(f"[dim]Calling {model} with {len(system_prompt)} char system prompt...[/dim]")
    try:
        out = call_openai(messages, model=model)
        console.print(Markdown(out))
    except Exception as e:
        console.print(f"[red]LLM call failed: {e}[/red]")
        console.print("[dim]Tip: `efren mind preview` works without any API key — it just renders the prompt.[/dim]")
        raise typer.Exit(1)
