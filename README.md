# Tilwell-Baco-Omega_ProductSheet

## Claude skill: vector-drawing

`.claude/skills/vector-drawing/` teaches Claude Code to produce clean vector art (SVG):

- **Trace a reference** image into SVG (`scripts/trace.py`, vtracer with palette cleanup) — for "draw it exactly like this".
- **Hand-draw** icons, logos and characters on a construction grid, then render and review every step (`scripts/render.py --grid / --compare / --overlay`).
- **Lint** the result for common defects (`scripts/lint_svg.py`).

Setup: `pip install -r .claude/skills/vector-drawing/requirements.txt`. Claude picks the skill up automatically when you ask it to draw, vectorize or trace an image (English or Thai).
