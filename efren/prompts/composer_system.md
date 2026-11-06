# Efren Composer — System Prompt Template

This is the template used by `Composer.compose_prompt()`. Not loaded directly — rendered programmatically.
See `efren/core/composer.py:compose_prompt`.

Structure:
1. Header: primary lens + composition weights
2. How to think (consolidated filters)
3. Heuristics (weighted)
4. Style lenses (detailed blocks)
5. Corpus grounding (set at init)
6. Output protocol (Efren table logic)
