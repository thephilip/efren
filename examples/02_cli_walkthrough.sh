#!/usr/bin/env bash
set -e
# Efren CLI walkthrough — run from project root

echo "=== 1. Init project with corpus ==="
efren init ./my_lab --corpus ./my_papers --name my_lab

echo ""
echo "=== 2. List baseline styles ==="
efren style list

echo ""
echo "=== 3. Inspect a style (The Magician) ==="
efren style show efren

echo ""
echo "=== 4. Create a composable mind (mix-match) ==="
efren mind create magician-alpha --mix efren=0.4,tesla=0.3,curie=0.3 --desc "Creative + visual + precise" --project ./my_lab

echo ""
echo "=== 5. Another mind — pure theorist ==="
efren mind create theorist --mix einstein=0.5,davinci=0.5 --project ./my_lab

echo ""
echo "=== 6. List minds ==="
efren mind list --project ./my_lab

echo ""
echo "=== 7. Table read (new Phase 0 — see the cushions/pockets) ==="
efren table --task "Design a low-cost water purifier from hardware store parts"
efren table --task "Design a low-cost water purifier from hardware store parts" --save /tmp/table.md

echo ""
echo "=== 8. Corpus search (new Phase 0 — citation ids) ==="
efren corpus search "SODIS" --project ./my_lab
efren corpus search "quantum resonance" --project ./my_lab  # shows corpus silent

echo ""
echo "=== 9. Conflict-aware mix (new Phase 0) ==="
efren mind create clash --mix tesla=0.5,edison=0.5 --project ./my_lab  # warns: edison ↔ tesla
efren style show tesla  # shows Conflicts with: / Compatible with:

echo ""
echo "=== 10. Preview prompt (no API key needed) ==="
efren mind preview magician-alpha --task "Design a low-cost water purifier from hardware store parts" --project ./my_lab

echo ""
echo "=== 11. Render full prompt to file (for any LLM) — now citation-required ==="
efren mind compose magician-alpha --task "Design a low-cost water purifier" --project ./my_lab --save /tmp/efren_prompt.md
echo "Saved to /tmp/efren_prompt.md — paste into ChatGPT/Claude/local LLM"
grep -q "CITATION REQUIRED" /tmp/efren_prompt.md && echo "✓ Citation enforcement present"
grep -q "corpus silent" /tmp/efren_prompt.md && echo "  (silent handling also present for unmatched queries)"

echo ""
echo "=== 12. Corpus ingest check ==="
efren corpus show --project ./my_lab

echo ""
echo "=== 13. (Optional) Call OpenAI if key is set ==="
if [ -n "$OPENAI_API_KEY" ]; then
  efren chat magician-alpha --task "Design a low-cost water purifier" --project ./my_lab
else
  echo "Skipping efren chat — set OPENAI_API_KEY to enable"
fi

echo ""
echo "=== 14. Try the opencode skill ==="
echo "In any opencode session, run /efren — skill at .opencode/skills/efren/SKILL.md"
