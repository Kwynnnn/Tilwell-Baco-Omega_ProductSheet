#!/usr/bin/env python3
"""Check an SVG for the problems that make vector drawings look broken.

    python lint_svg.py drawing.svg

Reports: missing viewBox, parse errors, points far outside the canvas,
unclosed filled paths, unused/duplicate ids, raster <image> embeds,
too many decimals, and overall complexity. Exit code 1 on errors.
"""
import re
import sys
import xml.etree.ElementTree as ET

NUM = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def strip(tag):
    return tag.split("}", 1)[-1]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    errors, warns = [], []
    text = open(path, encoding="utf-8").read()
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        print(f"ERROR: not valid XML: {e}")
        sys.exit(1)
    if strip(root.tag) != "svg":
        errors.append("root element is not <svg>")

    vb = root.get("viewBox")
    if not vb:
        errors.append("no viewBox: the drawing will not scale cleanly")
        x0 = y0 = 0
        try:
            vw = float(root.get("width", "0").rstrip("px"))
            vh = float(root.get("height", "0").rstrip("px"))
        except ValueError:
            vw = vh = 0
    else:
        x0, y0, vw, vh = [float(v) for v in re.split(r"[\s,]+", vb.strip())]

    ids, refs = {}, set()
    counts = {}
    long_decimals = 0
    out_of_bounds = 0
    for el in root.iter():
        tag = strip(el.tag)
        counts[tag] = counts.get(tag, 0) + 1
        if el.get("id"):
            ids[el.get("id")] = ids.get(el.get("id"), 0) + 1
        for k, v in el.attrib.items():
            for r in re.findall(r"url\(#([^)]+)\)", v):
                refs.add(r)
            if strip(k) == "href" and v.startswith("#"):
                refs.add(v[1:])
            if strip(k) == "href" and v.startswith("data:image"):
                errors.append("embedded raster image: this is not a real vector")
        if tag == "image":
            warns.append("<image> element present (raster inside SVG)")
        d = el.get("d")
        if d:
            nums = NUM.findall(d)
            long_decimals += sum(1 for n in nums if "." in n and len(n.split(".")[1]) > 3)
            fill = el.get("fill", "")
            if fill not in ("none", "") and not re.search(r"[zZ]\s*$", d.strip()):
                warns.append(f"filled path not closed with Z (id={el.get('id')})")
            # rough bounds check on absolute M/L coordinates only
            for m in re.finditer(r"[ML]\s*(-?[\d.]+)[ ,]+(-?[\d.]+)", d):
                x, y = float(m.group(1)), float(m.group(2))
                if vw and (x < x0 - vw * 0.5 or x > x0 + vw * 1.5 or
                           y < y0 - vh * 0.5 or y > y0 + vh * 1.5):
                    out_of_bounds += 1

    for i, c in ids.items():
        if c > 1:
            errors.append(f"duplicate id '{i}'")
    unused = [i for i in ids if i not in refs and i.startswith(("grad", "clip", "mask", "pat"))]
    if unused:
        warns.append(f"defs never referenced: {', '.join(unused[:8])}")
    if out_of_bounds:
        warns.append(f"{out_of_bounds} path points far outside the viewBox "
                     "(likely a coordinate mistake)")
    if long_decimals > 50:
        warns.append(f"{long_decimals} numbers with >3 decimals: round to 1-2")

    shapes = sum(counts.get(t, 0) for t in
                 ("path", "rect", "circle", "ellipse", "polygon", "polyline", "line"))
    print(f"{path}: viewBox={vb}, {shapes} shapes, {len(text)/1024:.1f} KB")
    print("  elements: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for w in warns:
        print(f"  WARN:  {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    if not warns and not errors:
        print("  OK")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
