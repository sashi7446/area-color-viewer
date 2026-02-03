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


def get_colors_from_image(image_path: str, verbose: bool = True) -> list[dict]:
    """Extract colors from image and return as list of dicts.

    Args:
        image_path: Path to input image
        verbose: Print progress messages

    Returns:
        List of dicts with keys: Hex, R, G, B, Count (sorted by count descending)
    """
    img = Image.open(image_path).convert("RGB")
    original_w, original_h = img.size
    original_total = original_w * original_h

    if verbose:
        print(f"元サイズ: {original_w} x {original_h} = {original_total:,} px")

    # Resize with nearest neighbor (no interpolation artifacts)
    if original_total > TARGET_PIXELS:
        scale = (TARGET_PIXELS / original_total) ** 0.5
        new_w = max(1, round(original_w * scale))
        new_h = max(1, round(original_h * scale))
        img = img.resize((new_w, new_h), Image.NEAREST)
        if verbose:
            print(f"圧縮後: {new_w} x {new_h} = {new_w * new_h:,} px")
    else:
        if verbose:
            print("圧縮不要")

    pixels = list(img.getdata())
    total = len(pixels)
    color_counts: Counter = Counter()

    if verbose:
        print(f"色を抽出中...")

    for i, (r, g, b) in enumerate(pixels):
        hex_color = rgb_to_hex(r, g, b)
        color_counts[hex_color] += 1

        if verbose and ((i + 1) % 50000 == 0 or i + 1 == total):
            pct = (i + 1) / total * 100
            print(f"  {i + 1:,} / {total:,} ({pct:.1f}%)", end="\r")

    if verbose:
        print()  # newline after progress

    # Convert to list of dicts sorted by count descending
    colors = []
    for hex_color, count in color_counts.most_common():
        r, g, b = hex_to_rgb(hex_color)
        colors.append({
            "Hex": hex_color,
            "R": r,
            "G": g,
            "B": b,
            "Count": count,
        })

    return colors


def save_colors_to_csv(colors: list[dict], output_path: str) -> None:
    """Save color data to CSV file.

    Args:
        colors: List of dicts with keys: Hex, R, G, B, Count
        output_path: Path to output CSV file
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Hex", "R", "G", "B", "Count"])
        for color in colors:
            writer.writerow([
                color["Hex"],
                color["R"],
                color["G"],
                color["B"],
                color["Count"],
            ])


def extract_colors(image_path: str, output_path: str) -> None:
    """Extract colors from image and save to CSV (legacy interface)."""
    colors = get_colors_from_image(image_path)
    save_colors_to_csv(colors, output_path)
    print(f"完了: {len(colors):,} 色を {output_path} に出力しました")


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
