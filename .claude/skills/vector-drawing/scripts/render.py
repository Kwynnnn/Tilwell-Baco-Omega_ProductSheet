#!/usr/bin/env python3
"""Render an SVG to PNG so you can LOOK at it before handing it over.

    python render.py drawing.svg                     # -> drawing.png
    python render.py drawing.svg --grid 10           # overlay a 10-unit grid
    python render.py drawing.svg --compare ref.png   # side-by-side with reference
    python render.py drawing.svg --overlay ref.png   # SVG over a faded reference

Always open the PNG with the Read tool and check proportions, symmetry,
alignment and gaps before saying the drawing is done.
"""
import argparse
import io
import re
import sys

try:
    import cairosvg
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Missing dependency. Run: pip install cairosvg pillow")


def view_box(svg_text):
    m = re.search(r'viewBox\s*=\s*"([^"]+)"', svg_text)
    if m:
        vals = [float(v) for v in re.split(r"[\s,]+", m.group(1).strip())]
        if len(vals) == 4:
            return vals
    w = re.search(r'<svg[^>]*\swidth\s*=\s*"([\d.]+)', svg_text)
    h = re.search(r'<svg[^>]*\sheight\s*=\s*"([\d.]+)', svg_text)
    if w and h:
        return [0, 0, float(w.group(1)), float(h.group(1))]
    return None


def render(svg_path, width, background):
    with open(svg_path, encoding="utf-8") as f:
        text = f.read()
    png = cairosvg.svg2png(bytestring=text.encode("utf-8"), output_width=width,
                           background_color=background)
    return Image.open(io.BytesIO(png)).convert("RGBA"), view_box(text)


def draw_grid(img, vb, step):
    if not vb:
        print("warning: no viewBox/width/height; grid skipped")
        return img
    x0, y0, vw, vh = vb
    sx, sy = img.width / vw, img.height / vh
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    try:
        font = ImageFont.load_default(size=max(10, img.width // 80))
    except TypeError:
        font = ImageFont.load_default()
    k = 0
    v = (x0 // step) * step
    while v <= x0 + vw:
        px = (v - x0) * sx
        major = k % 5 == 0
        d.line([(px, 0), (px, img.height)],
               fill=(255, 0, 80, 140 if major else 60), width=1)
        if major:
            d.text((px + 2, 2), f"{v:g}", fill=(255, 0, 80, 220), font=font)
        v += step
        k += 1
    k = 0
    v = (y0 // step) * step
    while v <= y0 + vh:
        py = (v - y0) * sy
        major = k % 5 == 0
        d.line([(0, py), (img.width, py)],
               fill=(0, 120, 255, 140 if major else 60), width=1)
        if major:
            d.text((2, py + 2), f"{v:g}", fill=(0, 120, 255, 220), font=font)
        v += step
        k += 1
    # centre lines help check symmetry
    cx, cy = (vw / 2) * sx, (vh / 2) * sy
    d.line([(cx, 0), (cx, img.height)], fill=(0, 170, 0, 160), width=1)
    d.line([(0, cy), (img.width, cy)], fill=(0, 170, 0, 160), width=1)
    return Image.alpha_composite(img, layer)


def fit(ref, size):
    ref = ref.convert("RGBA")
    scale = min(size[0] / ref.width, size[1] / ref.height)
    ref = ref.resize((round(ref.width * scale), round(ref.height * scale)),
                     Image.LANCZOS)
    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    canvas.paste(ref, ((size[0] - ref.width) // 2, (size[1] - ref.height) // 2), ref)
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg")
    ap.add_argument("-o", "--output", help="PNG path (default: next to the SVG)")
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--background", default="white",
                    help="'white', any CSS colour, or 'none' for transparent")
    ap.add_argument("--grid", type=float, default=None,
                    help="overlay a grid every N viewBox units, labelled every 5")
    ap.add_argument("--compare", help="reference image to place side by side")
    ap.add_argument("--overlay", help="reference image to put under the SVG at 35%%")
    args = ap.parse_args()

    bg = None if args.background == "none" else args.background
    img, vb = render(args.svg, args.width, bg)

    if args.overlay:
        ref = fit(Image.open(args.overlay), img.size)
        ref.putalpha(90)
        base = Image.new("RGBA", img.size, (255, 255, 255, 255))
        base = Image.alpha_composite(base, ref)
        svg_layer, _ = render(args.svg, args.width, None)
        img = Image.alpha_composite(base, svg_layer)
    if args.grid:
        img = draw_grid(img, vb, args.grid)
    if args.compare:
        ref = fit(Image.open(args.compare), img.size)
        gap = 16
        out = Image.new("RGBA", (img.width * 2 + gap, img.height),
                        (230, 230, 230, 255))
        out.paste(ref, (0, 0))
        out.paste(img, (img.width + gap, 0))
        d = ImageDraw.Draw(out)
        d.text((8, 8), "reference", fill=(200, 0, 0, 255))
        d.text((img.width + gap + 8, 8), "svg", fill=(200, 0, 0, 255))
        img = out

    out_path = args.output or re.sub(r"\.svg$", "", args.svg) + ".png"
    img.save(out_path)
    print(f"wrote {out_path} ({img.width}x{img.height}); viewBox={vb}")


if __name__ == "__main__":
    main()
