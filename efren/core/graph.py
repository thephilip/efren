"""Graph adapter — bridge efren corpus to graphify graph.

Detects graphify-out/graph.json built from corpus sources and uses it for
GraphRAG-style retrieval. Falls back gracefully if graphify not installed.

Usage:
  efren corpus graphify --path ./corpus    -> builds graphify-out/
  efren corpus graph-query "How does SODIS work?"
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
from typing import Optional, List, Dict

# repo checkout root (holds bench/, graphify-out/) when installed editable
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def find_graph(project_root: pathlib.Path) -> Optional[pathlib.Path]:
    """Find graph.json — check project graphify-out, then efren install dir."""
    candidates = [
        project_root / "graphify-out" / "graph.json",
        pathlib.Path.cwd() / "graphify-out" / "graph.json",
        _REPO_ROOT / "graphify-out" / "graph.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def has_graph(project_root: pathlib.Path) -> bool:
    return find_graph(project_root) is not None


def graph_info(project_root: pathlib.Path) -> Optional[Dict]:
    p = find_graph(project_root)
    if not p:
        return None
    try:
        data = json.loads(p.read_text())
        # graphify graph.json has nodes/edges
        return {
            "path": str(p),
            "nodes": len(data.get("nodes", [])),
            "edges": len(data.get("edges", [])),
            "directed": data.get("directed", False),
        }
    except Exception:
        return {"path": str(p), "nodes": 0, "edges": 0}


def query_graph(question: str, project_root: pathlib.Path, budget: int = 1500) -> Optional[str]:
    """Query existing graphify graph via `graphify query` CLI.

    Returns formatted markdown or None if graphify not available / no graph.
    """
    gpath = find_graph(project_root)
    if not gpath:
        return None
    # graphify binary
    bin_path = shutil.which("graphify")
    if not bin_path:
        return None
    # run graphify query from project_root so it finds graphify-out/graph.json
    try:
        result = subprocess.run(
            [bin_path, "query", question, "--budget", str(budget)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            # try fallback: run with explicit --graph
            result = subprocess.run(
                [bin_path, "query", question, "--budget", str(budget), "--graph", str(gpath)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        out = (result.stdout or "") + (result.stderr or "")
        if not out.strip() or "No graph found" in out or "graph.json not found" in out:
            return None
        # if output looks like error, return None
        if result.returncode != 0 and len(out.strip()) < 50:
            return None
        return out.strip()
    except Exception:
        return None


def _build_lightweight_graph(source_path: pathlib.Path, project_root: pathlib.Path) -> dict:
    """Offline fallback: build a tiny graph.json from corpus chunks without LLM.

    Nodes = top keywords per chunk + file nodes. Edges = co-occurrence.
    Enough for offline GraphRAG demo and bench.
    """
    try:
        import re

        # collect text files
        files: List[pathlib.Path] = []
        if source_path.is_file():
            files = [source_path]
        else:
            for ext in ("*.md", "*.txt", "*.yaml", "*.yml", "*.py", "*.json", "*.rst"):
                files.extend(source_path.rglob(ext))
        files = sorted(set(files))
        if not files:
            return {"ok": False, "error": f"no text files in {source_path}"}

        nodes: List[Dict] = []
        edges: List[Dict] = []
        # file nodes
        for f in files:
            rel = f.relative_to(source_path).as_posix() if f.is_relative_to(source_path) else f.name
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")[:2000]
            except Exception:
                text = ""
            fid = f"file:{rel}"
            nodes.append(
                {
                    "id": fid,
                    "label": rel,
                    "type": "file",
                    "description": text[:300].replace("\n", " "),
                    "source_location": str(f),
                }
            )
            # keyword nodes from this file
            words = re.findall(r"\w+", text.lower())
            # filter stop
            STOP = {"the", "and", "for", "with", "from", "this", "that", "have", "are", "was", "will", "your", "you", "not", "but", "all", "can", "also", "such", "then", "than", "which", "when", "what", "how", "why", "design", "task", "file", "corpus", "efren"}
            freq: Dict[str, int] = {}
            for w in words:
                if len(w) > 4 and w not in STOP:
                    freq[w] = freq.get(w, 0) + 1
            top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:6]
            for kw, cnt in top:
                nid = f"kw:{kw}"
                if not any(n["id"] == nid for n in nodes):
                    nodes.append({"id": nid, "label": kw, "type": "concept", "description": f"Keyword '{kw}' ({cnt} hits in {rel})"})
                edges.append({"source": fid, "target": nid, "type": "contains", "weight": cnt})
            # file-file edges if share keyword
        # write graph.json
        gdir = project_root / "graphify-out"
        gdir.mkdir(parents=True, exist_ok=True)
        graph_json = {
            "nodes": nodes,
            "edges": edges,
            "directed": False,
            "metadata": {"lightweight": True, "source": str(source_path), "files": len(files)},
        }
        (gdir / "graph.json").write_text(json.dumps(graph_json, indent=2))
        # minimal report
        (gdir / "GRAPH_REPORT.md").write_text(f"# Lightweight Graph (offline)\n\nSource: {source_path}\nFiles: {len(files)}\nNodes: {len(nodes)}\nEdges: {len(edges)}\n\nBuilt without LLM — keyword graph for offline GraphRAG.\n")
        return {"ok": True, "stdout": f"lightweight graph: {len(nodes)} nodes, {len(edges)} edges (offline, no LLM key)", "stderr": "", "returncode": 0, "lightweight": True}
    except Exception as e:
        return {"ok": False, "error": f"lightweight build failed: {e}"}


def build_graph(source_path: pathlib.Path, project_root: pathlib.Path, mode: str = "") -> dict:
    """Run `graphify <source_path>` to build graphify-out.

    Returns dict with status, logs. Falls back to lightweight offline graph if no LLM key.
    """
    bin_path = shutil.which("graphify")
    if not bin_path:
        # offline fallback if graphify not installed
        return _build_lightweight_graph(source_path, project_root)
    if not source_path.exists():
        return {"ok": False, "error": f"source not found: {source_path}"}
    args = [bin_path, str(source_path)]
    if mode:
        args.extend(["--mode", mode])
    try:
        result = subprocess.run(
            args,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=600,
        )
        ok = result.returncode == 0 and (project_root / "graphify-out" / "graph.json").exists()
        if ok:
            return {
                "ok": ok,
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-3000:],
                "returncode": result.returncode,
            }
        # check if failure is due to missing LLM key
        combined = (result.stdout + result.stderr).lower()
        if "no llm api key" in combined or "need semantic extraction" in combined:
            # try lightweight fallback
            fb = _build_lightweight_graph(source_path, project_root)
            if fb.get("ok"):
                fb["stdout"] = result.stdout[-1000:] + "\n[Fallback] " + fb["stdout"]
                fb["stderr"] = result.stderr[-1000:]
                return fb
        return {
            "ok": ok,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-3000:],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "graphify timed out (>600s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def graph_context_for_prompt(question: str, project_root: pathlib.Path, max_chars: int = 6000) -> Optional[str]:
    """Get graph context suitable for prompt injection.

    Tries graph query via CLI, falls back to lightweight keyword nodes, then None.
    Wraps result with citation header.
    """
    raw = query_graph(question, project_root, budget=1500)
    if raw:
        if len(raw) > max_chars:
            raw = raw[:max_chars] + f"\n... [truncated {len(raw)-max_chars} chars]"
        header = "[GraphRAG — graphify-out/graph.json | query: {}]".format(question[:80])
        return f"{header}\n{raw}\n---"
    # fallback: try lightweight node scan (offline, no LLM)
    nodes = fallback_graph_nodes(project_root, question, top_k=6)
    if nodes:
        lines = [f"[GraphRAG — lightweight | query: {question[:80]}]"]
        for n in nodes:
            label = n.get("label", n.get("id"))
            desc = n.get("description", "")[:200].replace("\n", " ")
            src = n.get("source_location", "")
            lines.append(f"- {label}: {desc}  [source: {src or n.get('id')}]")
        lines.append("---")
        ctx = "\n".join(lines)
        if len(ctx) > max_chars:
            ctx = ctx[:max_chars] + f"\n... [truncated {len(ctx)-max_chars} chars]"
        return ctx
    return None


def fallback_graph_nodes(project_root: pathlib.Path, query: str, top_k: int = 5) -> List[Dict]:
    """Lightweight fallback: read graph.json directly, BFS-like keyword match.

    No LLM needed — just scans node labels for query terms. Useful when graphify
    CLI not available or wants offline mode.
    """
    gpath = find_graph(project_root)
    if not gpath:
        return []
    try:
        data = json.loads(gpath.read_text())
        nodes = data.get("nodes", [])
        if not nodes:
            return []
        import re

        STOP = {"the", "and", "for", "with", "from", "this", "that", "have", "design", "task"}
        raw = re.findall(r"\w+", query.lower())
        terms = [t for t in raw if len(t) > 3 and t not in STOP]
        if not terms:
            terms = raw
        scored = []
        for n in nodes:
            label = (n.get("label") or n.get("id") or "").lower()
            desc = (n.get("description") or "").lower()
            text = f"{label} {desc}"
            score = sum(text.count(t) for t in terms)
            if score > 0:
                scored.append((score, n))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]
    except Exception:
        return []
