---
name: vector-drawing
description: Draw clean, well-proportioned vector art (SVG) — icons, logos, flat illustrations, characters, stickers, line art — and trace a reference image into an editable vector. Use whenever the user asks to draw, design, recreate, vectorize, trace or "convert to vector/SVG/AI" an image, or asks for an illustration that must not look distorted. Thai triggers too: วาดรูป, วาดเวกเตอร์, ทำเป็นเวกเตอร์, วาดตามแบบ, แปลงรูปเป็น SVG, ทำโลโก้, ไอคอน.
---

# Vector Drawing

The rule behind this skill: **never hand over a drawing you have not looked at.**
Hand-written SVG coordinates drift; the fix is to render, look, measure, fix — every time.

## Setup (once per session)

```bash
pip install -r .claude/skills/vector-drawing/requirements.txt
```

Scripts live in `.claude/skills/vector-drawing/scripts/` (call them as `S=.claude/skills/vector-drawing/scripts`).

| Script | What it does |
|---|---|
| `trace.py in.png out.svg --preset logo` | Raster reference → SVG (vtracer + palette cleanup) |
| `render.py file.svg [--grid 10] [--compare ref.png] [--overlay ref.png]` | SVG → PNG to inspect, with grid / side-by-side / onion-skin |
| `lint_svg.py file.svg` | Catches missing viewBox, stray points, unclosed paths, raster embeds |

## Step 1 — Pick the route

| The user gives you… | Route |
|---|---|
| A reference image and wants it **as vector / the same drawing** | **A. Trace** |
| A reference image and wants a **new drawing in that style / pose / layout** | **B. Hand-draw**, using the reference as an overlay guide |
| Only a description (icon, logo, mascot, illustration) | **B. Hand-draw** |
| A photo they want as a vector | **A. Trace** with `--preset photo`, or posterize style with `--preset illustration --colors 6` |

If the request is ambiguous ("วาดตามแบบนี้"), ask once: exact copy as vector (trace) or redraw in a cleaner style (hand-draw)?

## Route A — Trace a reference

1. Save the user's image to a working file (uploads are already on disk; use that path).
2. Pick a preset:
   - `logo` — flat colours, sharp corners (logos, icons, stickers, text)
   - `illustration` — flat colours, smoother curves (cartoon, flat art)
   - `lineart` — black & white sketches, signatures, ink drawings
   - `photo` — many colours, most detail
3. Run and inspect:
   ```bash
   python $S/trace.py ref.png out.svg --preset logo --colors 6
   python $S/render.py out.svg --compare ref.png
   ```
   Read the PNG. Compare edges, colours, small details.
4. Tune (one change at a time, re-render after each):
   - Blotchy / too many shapes → lower `--colors`, raise `--speckle 10`
   - Lost small details → raise `--colors`, lower `--speckle 2`
   - Corners rounded off (logos, text) → `--corner 30`
   - Wobbly edges from JPEG noise → `--blur 1.2`
   - Lineart too thin/thick → change `--threshold` (higher = more black)
   - Pixel art / geometric → `--polygon`
5. `python $S/lint_svg.py out.svg`, then deliver.

Optional cleanup after tracing: recolour fills to the exact brand hex codes the user gives you (edit the `fill=` values), and delete the white background path if they want transparency.

## Route B — Hand-draw an SVG

Read `references/svg-craft.md` before drawing anything non-trivial (characters, faces, animals, logos). It has the construction rules that prevent distortion. `examples/mascot.svg` is a small worked example: construction notes in a comment, mirrored parts via `<use>`, clipped shading, layered groups.

1. **Plan on paper first.** Before writing SVG, write a short plan:
   - canvas: `viewBox="0 0 W H"` (use round numbers: 512×512 icons, 800×600 scenes, 24×24 UI icons)
   - the **construction grid**: centre line, key horizontal lines (e.g. eye line, ground line), main proportions as numbers
   - a list of layers back → front, each as simple shapes (circle, ellipse, rect, rounded rect, path)
   - a palette of 3–6 hex colours
2. **Block in** with primitives only (circles, ellipses, rects) at the planned coordinates. Render with `--grid`:
   ```bash
   python $S/render.py draft.svg --grid 32
   ```
   Read the PNG. Check silhouette, proportions, symmetry against the green centre lines.
3. **Refine** shapes into paths only after the block-in reads correctly. Use symmetry tricks (draw half, mirror with `transform="translate(W,0) scale(-1,1)"`) instead of eyeballing the second side.
4. **Detail** last: highlights, shadows, line work, small features.
5. After **every** step: render → Read → list what's wrong → fix. Do at least 2 full review passes. Typical things to look for:
   - mismatched left/right (eyes, ears, arms)
   - parts floating apart or overlapping wrongly (neck not touching head)
   - shapes clipped by the canvas edge
   - inconsistent stroke widths
   - lines that should meet but leave a gap
6. If the user gave a reference for style/pose, use `--overlay ref.png` to onion-skin your SVG over it while blocking in.
7. `python $S/lint_svg.py final.svg`, then deliver.

## Delivering

- Save the final `.svg` (and a preview `.png` from `render.py --width 1200`) somewhere the user can open; send them with SendUserFile if available.
- Say which route you used and what to tweak if they want changes (colours, line weight, detail level).
- For Illustrator: the SVG opens directly (File → Open). For Figma: drag-drop the SVG. For PDF/EPS, convert with `cairosvg out.svg -o out.pdf`.
- If the Figma MCP is connected and the user wants an AI-generated illustration rather than a traced or hand-built one, `generate_vector_illustration` is an alternative — still render/inspect the result.

## Hard rules

- No `<image>` / base64 rasters inside the SVG: that is not a vector.
- Always include `viewBox`. Round coordinates to ≤2 decimals.
- Never claim it's done without having Read at least one rendered PNG of the final file.
- Don't recreate copyrighted characters or real brands' logos as "original"; tracing the user's own artwork/logo is fine.
