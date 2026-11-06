from pathlib import Path

import pytest

from efren.core.angles import extract_atoms, sample_angles
from efren.core.corpus import Corpus, CorpusConfig, CorpusSource
from efren.core.mind import Mind
from efren.styles.registry import load_registry

NOTES = """# Field notes

- Ceramic filters with 0.2 micron pores remove bacteria from water
- Activated carbon from coconut shells absorbs organics in water
- Gravity systems run without pumps and last longer than pumped ones
- Clay pots cool water by evaporation through porous walls
- Copper vessels kill bacteria by releasing ions over hours
"""

MORE = """- Sand beds host a biofilm layer that eats pathogens when flow is slow
- Sunlight heats water in black bottles until pathogens die
- Evaporation through porous ceramic also concentrates salts on walls
"""


def _corpus(tmp: Path) -> Corpus:
    (tmp / "notes.md").write_text(NOTES)
    (tmp / "more.md").write_text(MORE)
    cfg = CorpusConfig(name="t", sources=[CorpusSource(path=str(tmp))])
    return Corpus(cfg, tmp)


def test_extract_atoms_skips_headings(tmp_path):
    atoms = extract_atoms(_corpus(tmp_path))
    assert len(atoms) == 8
    assert not any(a.text.startswith("#") for a in atoms)
    assert all(a.citation.startswith("[source: ") for a in atoms)


def test_sample_angles_ranked_and_deterministic(tmp_path):
    corpus = _corpus(tmp_path)
    task = "Design a water filter that removes bacteria"
    a1 = sample_angles(corpus, task, top_k=3)
    a2 = sample_angles(corpus, task, top_k=3)
    assert a1 and len(a1) <= 3
    assert [[x.text for x in a.atoms] for a in a1] == [[x.text for x in a.atoms] for a in a2]
    assert all(len(a.atoms) == 3 for a in a1)
    assert [a.score for a in a1] == sorted((a.score for a in a1), reverse=True)
    # every angle hooks to the task through at least one atom
    assert all(max(x.relevance for x in a.atoms) > 0 for a in a1)


def test_beta_shifts_toward_unavailability(tmp_path):
    corpus = _corpus(tmp_path)
    task = "Design a water filter that removes bacteria"
    safe = sample_angles(corpus, task, top_k=1, beta=0.0)[0]
    alien = sample_angles(corpus, task, top_k=1, beta=1.0)[0]
    assert alien.unavailability >= safe.unavailability
    assert safe.coherence >= alien.coherence


def test_sample_angles_fail_closed(tmp_path):
    corpus = _corpus(tmp_path)
    assert sample_angles(corpus, "quantum reactor shielding") == []
    with pytest.raises(ValueError):
        sample_angles(corpus, "water", beta=1.5)


def test_mind_render_angles_opt_in(tmp_path):
    reg = load_registry()
    corpus = _corpus(tmp_path)
    mind = Mind.from_mix_string(name="t", mix="efren=1.0", registry=reg)
    task = "Design a water filter that removes bacteria"
    assert "Unseen angles" not in mind.render_prompt(registry=reg, corpus=corpus, task=task)
    prompt = mind.render_prompt(registry=reg, corpus=corpus, task=task, angles=2)
    assert "Unseen angles" in prompt
    assert "[source: " in prompt.split("Unseen angles", 1)[1]


def test_judge_pair_maps_swapped_positions_back():
    from efren.core.bench import judge_pair

    reply = '{"novelty_1": 2, "novelty_2": 5, "feasibility_1": 4, "feasibility_2": 3, "winner": "2", "reason": "x"}'
    # B shown first when swapped, so response 1 is B
    j = judge_pair("t", "A out", "B out", lambda m: "Sure:\n" + reply, swap=True)
    assert (j["novelty_a"], j["novelty_b"], j["winner"]) == (5, 2, "a")
    j = judge_pair("t", "A out", "B out", lambda m: reply, swap=False)
    assert (j["novelty_a"], j["novelty_b"], j["winner"]) == (2, 5, "b")
