# SVG craft: drawing without distortion

Most "wonky" AI vector drawings come from three causes: no construction plan,
coordinates guessed per-shape instead of derived from shared guide lines, and
no visual check. This file fixes the first two; `render.py` fixes the third.

## 1. Construction before drawing

Write the guides down as numbers, then derive every shape from them.

```
viewBox 0 0 512 512, centre x = 256
head:  circle cx=256 cy=200 r=120     -> head spans y 80..320
eye line   y = 200 (half the head height for cartoons, a bit lower for cute)
eye spacing: eyes at x = 256 ± 45, r = 18
mouth line y = 255
body: ellipse cx=256 cy=400 rx=110 ry=90 -> top at y=310 overlaps head by 10 (no gap)
```

If a value isn't derived from a guide, it will drift.

## 2. Proportion cheat sheet

| Subject | Proportions |
|---|---|
| Cute mascot / chibi | head ≈ 1/2 – 2/3 of total height; eyes big, low on face, wide apart |
| Cartoon human | 3–5 heads tall; shoulders ≈ 2 head widths |
| Realistic human | 7.5 heads tall; eyes at half the head height; elbows at waist |
| Face (front) | eye width = gap between eyes; nose bottom ≈ 2/3 down from brow to chin; mouth corners under pupils |
| Animals | build from 3 masses (head, chest, hips) linked by a spine curve, then legs |
| Icons (24 grid) | 2px padding (live area 20×20), stroke 2, round caps/joins, align to whole/half pixels |
| Logos | build on a circle/square grid; reuse the same radius for every corner |

## 3. Symmetry

Draw one side, mirror the other — never eyeball both:

```svg
<g id="eye-left"><ellipse cx="211" cy="200" rx="18" ry="22"/></g>
<use href="#eye-left" transform="translate(512,0) scale(-1,1)"/>
```

(`translate(W,0) scale(-1,1)` mirrors around x = W/2.)

Do **not** mirror things that depend on light direction: eye highlights,
shadows and shine must sit on the same side for both copies, so draw them
separately after the mirrored shapes. `examples/mascot.svg` shows this.

## 4. Prefer primitives, then booleans-by-layering

- Circle/ellipse/rect with `rx` cover most of a cartoon. Use paths for what they can't do.
- Overlap shapes instead of tracing outlines exactly. For shading, clip a copy of the shape offset away from the light (`<clipPath>` of the base shape) so the shadow can never spill outside it, as `examples/mascot.svg` does.
- Same-colour shapes that overlap merge visually; no need for perfect joins.

## 5. Writing good paths

- Use cubic `C` with handles roughly 1/3 of the segment length, tangent to the curve — smooth joins need the incoming and outgoing handles collinear (or just use `S`).
- A circle-ish arc with cubic: handle length = 0.552 × radius.
- Fewer points = smoother. If a curve needs >8 points, split it into separate shapes.
- Close filled paths with `Z`.
- Absolute commands (uppercase) are easier to reason about than relative ones.

## 6. Strokes and line art

- Choose one or two stroke weights for the whole piece (e.g. 6 outline, 3 detail) and keep them.
- `stroke-linecap="round" stroke-linejoin="round"` for friendly art.
- Put outlines on a group: `<g fill="none" stroke="#2b2b2b" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">`.
- `vector-effect="non-scaling-stroke"` if shapes are scaled with transforms.

## 7. Colour

- 3–6 colours: base, shadow (base darkened ~15%), highlight (lightened ~20%), outline, accent.
- Flat shading: one shadow shape per mass, all lit from the same side (top-left is the default).
- Gradients sparingly; define them in `<defs>` with `gradientUnits="userSpaceOnUse"` when shared.

## 8. File hygiene

- Root: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" width="W" height="H">`.
- Group and id by part (`id="head"`, `id="arm-left"`) so the user can edit in Illustrator/Figma.
- Order layers back → front.
- Round to 1–2 decimals; no embedded rasters; no unused `<defs>`.

## 9. Review checklist (run on every render)

1. Silhouette readable at 64px? (`render.py --width 64`)
2. Symmetric parts actually symmetric against the green centre line?
3. Every part touches what it should (no floating ears/necks/limbs)?
4. Nothing clipped by the canvas; even margins?
5. Consistent stroke weights and light direction?
6. Does it match the reference / brief? List differences, fix the biggest first.
