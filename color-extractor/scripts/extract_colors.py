#!/usr/bin/env python3
"""Extract all color codes from an image and output as CSV."""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

TARGET_PIXELS = 500000


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def extract_colors(image_path: str, output_path: str) -> None:
    img = Image.open(image_path).convert("RGB")
    original_w, original_h = img.size
    original_total = original_w * original_h

    print(f"元サイズ: {original_w} x {original_h} = {original_total:,} px")

    # Resize with nearest neighbor (no interpolation artifacts)
    if original_total > TARGET_PIXELS:
        scale = (TARGET_PIXELS / original_total) ** 0.5
        new_w = max(1, round(original_w * scale))
        new_h = max(1, round(original_h * scale))
        img = img.resize((new_w, new_h), Image.NEAREST)
        print(f"圧縮後: {new_w} x {new_h} = {new_w * new_h:,} px")
    else:
        new_w, new_h = original_w, original_h
        print("圧縮不要")

    pixels = list(img.getdata())
    total = len(pixels)
    color_counts: Counter = Counter()

    print(f"色を抽出中...")
    for i, (r, g, b) in enumerate(pixels):
        hex_color = rgb_to_hex(r, g, b)
        color_counts[hex_color] += 1

        if (i + 1) % 50000 == 0 or i + 1 == total:
            pct = (i + 1) / total * 100
            print(f"  {i + 1:,} / {total:,} ({pct:.1f}%)", end="\r")

    print()  # newline after progress

    # Sort by count descending
    sorted_colors = color_counts.most_common()

    # Write CSV with Hex, R, G, B, Count
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Hex", "R", "G", "B", "Count"])
        for hex_color, count in sorted_colors:
            r, g, b = hex_to_rgb(hex_color)
            writer.writerow([hex_color, r, g, b, count])

    print(f"完了: {len(sorted_colors):,} 色を {output_path} に出力しました")


def main():
    parser = argparse.ArgumentParser(description="Extract color codes from image to CSV")
    parser.add_argument("image", help="Input image path")
    parser.add_argument("-o", "--output", default="colors.csv", help="Output CSV path (default: colors.csv)")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: {args.image} not found", file=sys.stderr)
        sys.exit(1)

    extract_colors(args.image, args.output)


if __name__ == "__main__":
    main()