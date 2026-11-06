"""Corpus — pluggable knowledge base set at init time."""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field

try:
    from efren.core.graph import has_graph, graph_context_for_prompt, graph_info

    _HAS_GRAPH_SUPPORT = True
except ImportError:
    _HAS_GRAPH_SUPPORT = False
    has_graph = lambda *a, **kw: False  # type: ignore
    graph_context_for_prompt = lambda *a, **kw: None  # type: ignore
    graph_info = lambda *a, **kw: None  # type: ignore


class CorpusSource(BaseModel):
    path: str  # file or directory or URL
    kind: str = "auto"  # auto | markdown | pdf | text | url
    include_glob: str = "**/*"
    exclude_glob: Optional[str] = None


class CorpusConfig(BaseModel):
    name: str
    description: str = ""
    sources: List[CorpusSource] = Field(default_factory=list)
    chunk_size: int = 1200
    chunk_overlap: int = 150
    embedding_model: Optional[str] = None  # e.g., "sentence-transformers/all-MiniLM-L6-v2"
    vector_store: str = "none"  # none | chroma | jsonl | graph

    @classmethod
    def from_yaml(cls, path: pathlib.Path) -> "CorpusConfig":
        return cls(**yaml.safe_load(path.read_text()))

    def to_yaml(self, path: pathlib.Path) -> None:
        path.write_text(yaml.safe_dump(self.model_dump(), sort_keys=False, allow_unicode=True))


@dataclass
class Chunk:
    id: str
    source: str
    text: str
    meta: dict


class Corpus:
    """Lightweight corpus manager. Ingests files into chunks, optional vector store.

    Corpus is SET AT INIT — this is the core design: efren init --corpus ./my_papers
    creates a CorpusConfig that all downstream minds are grounded in.
    """

    def __init__(self, config: CorpusConfig, root: pathlib.Path):
        self.config = config
        self.root = root

    @classmethod
    def load(cls, project_root: pathlib.Path) -> "Corpus":
        cfg_path = project_root / "corpus.yaml"
        if not cfg_path.exists():
            # empty corpus
            return cls(CorpusConfig(name="empty"), project_root)
        cfg = CorpusConfig.from_yaml(cfg_path)
        return cls(cfg, project_root)

    def ingest(self) -> List[Chunk]:
        chunks: List[Chunk] = []
        for src in self.config.sources:
            p = pathlib.Path(src.path)
            if not p.is_absolute():
                p = (self.root / p).resolve()
            if not p.exists():
                continue
            files = self._collect_files(p, src)
            for f in files:
                text = self._read_file(f)
                if not text.strip():
                    continue
                for i, c in enumerate(self._chunk_text(text)):
                    cid = hashlib.sha256(f"{f}:{i}:{c[:32]}".encode()).hexdigest()[:12]
                    chunks.append(Chunk(id=cid, source=str(f), text=c, meta={"source_kind": src.kind}))
        return chunks

    def _collect_files(self, path: pathlib.Path, src: CorpusSource) -> List[pathlib.Path]:
        if path.is_file():
            return [path]
        # directory
        import fnmatch

        all_files = list(path.rglob("*"))
        out = []
        for f in all_files:
            if not f.is_file():
                continue
            rel = f.relative_to(path).as_posix()
            # handle glob: "**/*" should match all files including top-level
            if src.include_glob not in ("**/*", "**", "*"):
                if not fnmatch.fnmatch(rel, src.include_glob) and not pathlib.PurePath(rel).match(src.include_glob):
                    continue
            if src.exclude_glob and (fnmatch.fnmatch(rel, src.exclude_glob) or pathlib.PurePath(rel).match(src.exclude_glob)):
                continue
            # only text-like by default
            if f.suffix.lower() not in {".md", ".txt", ".yaml", ".yml", ".json", ".tex", ".rst", ".py"}:
                # allow but skip binaries
                if f.suffix.lower() in {".pdf"} and src.kind in ("pdf", "auto"):
                    out.append(f)
                elif f.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json", ".tex", ".rst"}:
                    out.append(f)
                else:
                    # try reading as text anyway for .md/.txt variants
                    continue
            else:
                out.append(f)
        return sorted(out)

    def _read_file(self, path: pathlib.Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _chunk_text(self, text: str) -> List[str]:
        # simple sliding window on characters; swap for token-based if needed
        n = self.config.chunk_size
        overlap = self.config.chunk_overlap
        if len(text) <= n:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + n, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        return chunks

    def search(self, query: str, top_k: int = 5) -> List[Chunk]:
        """Keyword search — ranks chunks by term overlap (case-insensitive).

        Lightweight replacement for embeddings; swap with vector store when available.
        """
        if not query.strip():
            return self.ingest()[:top_k]
        chunks = self.ingest()
        if not chunks:
            return []
        import re

        STOP = {
            "the", "and", "for", "with", "from", "this", "that", "have", "has", "are", "was", "were",
            "been", "being", "will", "would", "could", "should", "about", "into", "over", "under",
            "your", "you", "not", "but", "all", "any", "can", "had", "also", "such", "then", "than",
            "which", "when", "what", "how", "why", "design", "task",
        }
        # tokenize on non-word chars, ignore short/stop words
        raw = re.findall(r"\w+", query.lower())
        q_terms = [t for t in raw if len(t) > 3 and t not in STOP]
        if not q_terms:
            # fallback to longer raw tokens
            q_terms = [t for t in raw if t not in STOP]
        if not q_terms:
            q_terms = [query.lower()]
        scored: list[tuple[int, Chunk]] = []
        for c in chunks:
            text_low = c.text.lower()
            # score = sum of term frequencies + bonus for phrase match
            score = sum(text_low.count(t) for t in q_terms)
            if query.lower() in text_low:
                score += 5
            # also boost if term appears in filename
            if any(t in pathlib.Path(c.source).name.lower() for t in q_terms):
                score += 2
            if score > 0:
                scored.append((score, c))
        if not scored:
            return []
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def prompt_context(self, max_chars: int = 8000, query: str | None = None) -> str:
        """Build a context block. If query given, rank by relevance (citation-friendly).

        Vector store options: none (keyword), chroma (embeddings), graph (graphify).
        Tries graph first if available.
        """
        # Try graph backend first (if enabled or auto-detected)
        if _HAS_GRAPH_SUPPORT and query and (self.config.vector_store == "graph" or has_graph(self.root)):
            gctx = graph_context_for_prompt(query, self.root, max_chars=max_chars)
            if gctx:
                return gctx
            # if graph exists but query returned nothing, fall through to keyword
            # (don't return silent yet — keyword might still hit)

        chunks = self.ingest()
        if not chunks:
            # also check if graph might have nodes even when no files ingested via chunk path
            if _HAS_GRAPH_SUPPORT and has_graph(self.root):
                gctx = graph_context_for_prompt(query or "", self.root, max_chars=max_chars) if query else None
                if gctx:
                    return gctx
            return "(no corpus ingested — add sources to corpus.yaml and re-run `efren corpus ingest`)"
        # if query provided, rank and select top relevant
        if query:
            ranked = self.search(query, top_k=20)
            if ranked:
                chunks = ranked
            else:
                # corpus silent for this query — signal explicitly
                # but also try graph silent is explicit
                return f"(corpus silent for query '{query}' — no matching chunks. Reason from first principles and flag as (corpus silent))"
        # take chunks up to budget (now query-ranked if applicable)
        buf = []
        total = 0
        for c in chunks:
            header = f"[source: {pathlib.Path(c.source).name} | id: {c.id}]"
            block = f"{header}\n{c.text}\n---"
            if total + len(block) > max_chars:
                break
            buf.append(block)
            total += len(block)
        return "\n".join(buf)

    def graph_status(self) -> dict | None:
        if not _HAS_GRAPH_SUPPORT:
            return None
        return graph_info(self.root)
