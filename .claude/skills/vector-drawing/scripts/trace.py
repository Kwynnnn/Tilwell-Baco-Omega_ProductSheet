#!/usr/bin/env python3
"""Trace a raster reference image (PNG/JPG/WebP) into a clean SVG.

Use this whenever the user wants a drawing that follows a reference image:
tracing keeps the real proportions, which hand-written coordinates rarely do.

    python trace.py input.png output.svg --preset logo --colors 6

Presets:
  logo         flat colours, sharp corners, few shapes (logos, icons, stickers)
  illustration flat colours, smoother curves (cartoons, flat illustrations)
  lineart      black-and-white line drawing / sketch / signature
  photo        many colours, most detail (largest file)
"""
import argparse
import os
import sys
import tempfile

try:
    import vtracer
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    sys.exit("Missing dependency. Run: pip install vtracer pillow cairosvg")

PRESETS = {
    "logo": dict(colormode="color", hierarchical="stacked", mode="spline",
                 filter_speckle=8, color_precision=6, layer_difference=24,
                 corner_threshold=45, length_threshold=4.0, splice_threshold=45,
                 path_precision=2),
    "illustration": dict(colormode="color", hierarchical="stacked", mode="spline",
                         filter_speckle=4, color_precision=6, layer_difference=16,
                         corner_threshold=60, length_threshold=4.0,
                         splice_threshold=45, path_precision=2),
    "lineart": dict(colormode="binary", mode="spline", filter_speckle=4,
                    corner_threshold=60, length_threshold=4.0,
                    splice_threshold=45, path_precision=2),
    "photo": dict(colormode="color", hierarchical="stacked", mode="spline",
                  filter_speckle=2, color_precision=8, layer_difference=8,
                  corner_threshold=60, length_threshold=3.5,
                  splice_threshold=45, path_precision=2),
}


def preprocess(src, max_size, colors, blur, threshold, lineart):
    """Normalise the reference so the tracer produces fewer, cleaner shapes."""
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        img = bg
    img = img.convert("RGB")

    # Upscale small images (tracing needs pixels to find smooth curves),
    # downscale huge ones (speed, fewer speckles).
    longest = max(img.size)
    if longest < 512:
        scale = 1024 / longest
        # BILINEAR, not LANCZOS: Lanczos overshoots and paints light halos
        # around dark shapes, which the tracer then turns into white outlines.
        img = img.resize((round(img.width * scale), round(img.height * scale)),
                         Image.BILINEAR)
    elif longest > max_size:
        scale = max_size / longest
        img = img.resize((round(img.width * scale), round(img.height * scale)),
                         Image.BOX)

    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))

    if lineart:
        g = ImageOps.autocontrast(img.convert("L"))
        img = g.point(lambda p: 0 if p < threshold else 255).convert("RGB")
    elif colors:
        # Reduce to a fixed palette: the biggest single win for clean flat art.
        # Octree + k-means keeps small but distinct colours (eyes, outlines);
        # median-cut wastes slots on near-identical whites from JPEG noise.
        pal = img.quantize(colors=colors, method=Image.Quantize.FASTOCTREE,
                           kmeans=3, dither=Image.Dither.NONE)
        # Octree's own pixel assignment is by tree bucket, not nearest colour,
        # and can paint edge pixels white; remap every pixel to its nearest
        # palette entry instead.
        img = img.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB")
        # Anti-aliased edges become thin "halo" bands of an in-between colour;
        # a mode filter absorbs them into the neighbouring flat colour.
        img = img.filter(ImageFilter.ModeFilter(5))
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--preset", choices=PRESETS, default="illustration")
    ap.add_argument("--colors", type=int, default=None,
                    help="reduce to N colours before tracing (default: 8 for "
                         "logo/illustration, none for photo)")
    ap.add_argument("--blur", type=float, default=None,
                    help="Gaussian blur radius before tracing; smooths JPEG noise "
                         "(default 0.8, 0 for lineart)")
    ap.add_argument("--threshold", type=int, default=128,
                    help="lineart only: grey level that becomes black (0-255)")
    ap.add_argument("--max-size", type=int, default=2000,
                    help="downscale reference so its longest side is at most this")
    ap.add_argument("--speckle", type=int, default=None,
                    help="override: drop blobs smaller than N px")
    ap.add_argument("--corner", type=int, default=None,
                    help="override: corner threshold in degrees (lower = sharper)")
    ap.add_argument("--polygon", action="store_true",
                    help="straight segments only (pixel/geometric art)")
    args = ap.parse_args()

    params = dict(PRESETS[args.preset])
    lineart = args.preset == "lineart"
    colors = args.colors
    if colors is None and args.preset in ("logo", "illustration"):
        colors = 8
    blur = args.blur if args.blur is not None else (0 if lineart else 0.8)
    if args.speckle is not None:
        params["filter_speckle"] = args.speckle
    if args.corner is not None:
        params["corner_threshold"] = args.corner
    if args.polygon:
        params["mode"] = "polygon"

    img = preprocess(args.input, args.max_size, colors, blur, args.threshold, lineart)
    with tempfile.TemporaryDirectory() as tmp:
        prepped = os.path.join(tmp, "prepped.png")
        img.save(prepped)
        vtracer.convert_image_to_svg_py(prepped, args.output, **params)

    # vtracer emits width/height only; add a viewBox so the SVG scales cleanly.
    with open(args.output, encoding="utf-8") as f:
        svg = f.read()
    if "viewBox" not in svg:
        svg = svg.replace(
            f'width="{img.width}" height="{img.height}"',
            f'width="{img.width}" height="{img.height}" '
            f'viewBox="0 0 {img.width} {img.height}"', 1)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(svg)

    n_paths = svg.count("<path")
    size_kb = os.path.getsize(args.output) / 1024
    print(f"wrote {args.output}: {n_paths} paths, {size_kb:.1f} KB, "
          f"{img.width}x{img.height}, preset={args.preset}, colors={colors}")
    if n_paths > 1500:
        print("hint: many paths. Try fewer --colors, a larger --speckle, or "
              "--preset logo for a cleaner result.")


if __name__ == "__main__":
    main()
