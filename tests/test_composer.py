from efren.styles.registry import load_registry
from efren.core.mind import Mind
from efren.core.corpus import Corpus, CorpusConfig


def test_registry_loads_baselines():
    reg = load_registry()
    assert "efren" in reg
    assert "tesla" in reg
    assert "curie" in reg
    assert len(reg) >= 7


def test_composer_parse_mix():
    from efren.core.composer import Composer
    reg = load_registry()
    c = Composer(reg)
    w = c.parse_mix("tesla=0.5,efren=0.3,curie=0.2")
    assert abs(sum(x.weight for x in w) - 1.0) < 1e-6
    # equal weights when no = given
    w2 = c.parse_mix("tesla,efren")
    assert len(w2) == 2
    assert abs(w2[0].weight - 0.5) < 1e-6


def test_mind_render():
    from pathlib import Path
    reg = load_registry()
    mind = Mind.from_mix_string(name="t", mix="efren=0.5,tesla=0.5", registry=reg)
    corpus = Corpus(CorpusConfig(name="empty"), root=Path("/tmp"))
    prompt = mind.render_prompt(registry=reg, corpus=corpus, task="test task")
    assert "Efren" in prompt
    assert "tesla" in prompt.lower()
    assert "test task" in prompt
    # output protocol present
    assert "Magician" in prompt or "kick shot" in prompt.lower() or "Angles" in prompt


def test_corpus_ingest():
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "note.md"
        p.write_text("hello world " * 100)
        cfg = CorpusConfig(name="t", sources=[])
        # no sources -> empty context
        c = Corpus(cfg, Path(tmp))
        assert "no corpus" in c.prompt_context().lower()
