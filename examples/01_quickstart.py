"""Efren quickstart — programmatic API (no CLI needed)."""

from pathlib import Path
from efren.core.corpus import Corpus, CorpusConfig, CorpusSource
from efren.core.mind import Mind
from efren.styles.registry import load_registry
from efren.core.llm import build_messages, dry_run_preview

# 1. Corpus is SET AT INIT
corpus_cfg = CorpusConfig(
    name="demo-corpus",
    description="Demo notes",
    sources=[CorpusSource(path="./examples/corpus", kind="auto")],
)
# For this demo, use the project root as corpus root (empty is fine)
corpus = Corpus(config=corpus_cfg, root=Path(__file__).parent.parent)

# 2. Load baseline styles (7 built-ins including Efren The Magician)
registry = load_registry()
print(f"Loaded styles: {sorted(registry.keys())}")
# -> ['curie', 'davinci', 'edison', 'efren', 'einstein', 'hopper', 'tesla']

# 3. Create a consolidated mind by mix-matching
mind = Mind.from_mix_string(
    name="magician-v1",
    mix="efren=0.4,tesla=0.3,curie=0.3",
    registry=registry,
    description="Creative angles + visual simulation + meticulous verification",
)
print(f"Mind: {mind.name} — {', '.join(f'{w.style_id}={w.weight:.2f}' for w in mind.composition)}")

# 4. Render a corpus-grounded, composable system prompt for any task
task = "Design a low-cost water purification device that can be built from hardware store parts."
system_prompt = mind.render_prompt(registry=registry, corpus=corpus, task=task)

print("\n" + "="*60)
print(f"System prompt: {len(system_prompt)} chars")
print(system_prompt[:2000])
print("...\n")

# 5. Use with ANY LLM (OpenAI, Anthropic, local, etc.)
messages = build_messages(system_prompt, task)
print(f"Messages ready for LLM: {len(messages)} messages")
print(f"System: {len(messages[0]['content'])} chars, User: {len(messages[1]['content'])} chars")

# 6. Preview without calling an LLM
print("\n" + dry_run_preview(system_prompt, task, max_chars=1500))

# 7. To actually call an LLM (requires OPENAI_API_KEY):
# from efren.core.llm import call_openai
# response = call_openai(messages, model="gpt-4o-mini")
# print(response)

# 8. Save/load minds as YAML (shareable, versionable)
mind.save(Path("/tmp/magician-v1.yaml"))
print(f"Saved mind to /tmp/magician-v1.yaml")
loaded = Mind.load(Path("/tmp/magician-v1.yaml"))
assert loaded.name == mind.name
print("Reloaded OK — mind is portable.")

# 9. Try other mixes
for mix in ["efren=1.0", "einstein=0.5,davinci=0.5", "edison=0.4,hopper=0.3,curie=0.3"]:
    m = Mind.from_mix_string(name="probe", mix=mix, registry=registry)
    prompt = m.render_prompt(registry=registry, task="Propose a novel experiment")
    print(f"\nMix {mix:40} -> prompt {len(prompt)} chars, primary={m.composition[0].style_id}")
