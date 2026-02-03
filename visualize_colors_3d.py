#!/usr/bin/env python3
"""3D scatter plot visualization of color data in OKLCH color space."""

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go


def srgb_to_linear(c: float) -> float:
    """Convert sRGB component (0-1) to linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_srgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert linear sRGB to OKLab.

    Based on Björn Ottosson's formulas:
    https://bottosson.github.io/posts/oklab/
    """
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    # Cube root (handle negative values)
    l_ = np.cbrt(l)
    m_ = np.cbrt(m)
    s_ = np.cbrt(s)

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_val = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return L, a, b_val


def oklab_to_oklch(L: float, a: float, b: float) -> tuple[float, float, float]:
    """Convert OKLab to OKLCH (polar coordinates)."""
    C = math.sqrt(a * a + b * b)
    H = math.atan2(b, a)  # in radians
    H_deg = math.degrees(H)
    if H_deg < 0:
        H_deg += 360
    return L, C, H_deg


def rgb_to_oklch(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB (0-255) to OKLCH.

    Returns:
        tuple: (L, C, H) where L is 0-1, C is 0-~0.4, H is 0-360 degrees
    """
    # Normalize to 0-1
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Convert to linear sRGB
    r_lin = srgb_to_linear(r_norm)
    g_lin = srgb_to_linear(g_norm)
    b_lin = srgb_to_linear(b_norm)

    # Convert to OKLab
    L, a, b_val = linear_srgb_to_oklab(r_lin, g_lin, b_lin)

    # Convert to OKLCH
    return oklab_to_oklch(L, a, b_val)


def load_colors_csv(csv_path: str) -> list[dict]:
    """Load color data from CSV file."""
    colors = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            colors.append({
                "Hex": row["Hex"],
                "R": int(row["R"]),
                "G": int(row["G"]),
                "B": int(row["B"]),
                "Count": int(row["Count"]),
            })
    return colors


def create_3d_scatter(colors: list[dict], output_path: str, max_count: int | None = None) -> None:
    """Create 3D scatter plot using Plotly."""
    # Determine max_count for opacity scaling
    if max_count is None:
        # Calculate average of top 5 counts
        sorted_counts = sorted([c["Count"] for c in colors], reverse=True)
        top_counts = sorted_counts[:5]
        if top_counts:
            max_count = int(sum(top_counts) / len(top_counts))
        else:
            max_count = 1  # Fallback
        print(f"Automatically calculated max_count (avg of top 5): {max_count:,}")
    else:
        print(f"Using fixed max_count: {max_count:,}")

    # Process colors and convert to OKLCH
    data = []
    for color in colors:
        L, C, H = rgb_to_oklch(color["R"], color["G"], color["B"])
        H_rad = math.radians(H)

        # Cylindrical coordinates: x = C*cos(H), y = C*sin(H), z = L
        x = C * math.cos(H_rad)
        y = C * math.sin(H_rad)
        z = L

        # Opacity: sqrt mapping from count (makes low-count points more visible)
        opacity = min(math.sqrt(color["Count"] / max_count), 1.0)

        data.append({
            "x": x,
            "y": y,
            "z": z,
            "opacity": opacity,
            "hex": color["Hex"],
            "count": color["Count"],
            "L": L,
            "C": C,
            "H": H,
        })

    # Extract arrays for plotting
    x_vals = [d["x"] for d in data]
    y_vals = [d["y"] for d in data]
    z_vals = [d["z"] for d in data]

    # Create RGBA colors with per-point opacity (black with varying transparency)
    rgba_colors = [
        f"rgba(0, 0, 0, {d['opacity']:.4f})"
        for d in data
    ]

    hover_texts = [
        f"Hex: {d['hex']}<br>"
        f"Count: {d['count']:,}<br>"
        f"L: {d['L']:.3f}<br>"
        f"C: {d['C']:.3f}<br>"
        f"H: {d['H']:.1f}°"
        for d in data
    ]

    # Create figure with monochromatic points (opacity via RGBA)
    fig = go.Figure(data=[go.Scatter3d(
        x=x_vals,
        y=y_vals,
        z=z_vals,
        mode="markers",
        marker=dict(
            size=3,
            color=rgba_colors,
        ),
        text=hover_texts,
        hoverinfo="text",
    )])

    # Update layout
    fig.update_layout(
        title=dict(
            text="Color Distribution in OKLCH Space",
            font=dict(size=20),
        ),
        scene=dict(
            xaxis=dict(title="C × cos(H)", range=[-0.4, 0.4]),
            yaxis=dict(title="C × sin(H)", range=[-0.4, 0.4]),
            zaxis=dict(title="L (Lightness)", range=[0, 1]),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=1.5),
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        paper_bgcolor="white",
    )

    # Save as HTML
    fig.write_html(output_path, include_plotlyjs=True, full_html=True)
    print(f"Saved 3D scatter plot to: {output_path}")
    print(f"Total colors plotted: {len(data):,}")


def main():
    parser = argparse.ArgumentParser(
        description="Create 3D scatter plot of colors in OKLCH space"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="dashboard_colors.csv",
        help="Input CSV file (default: dashboard_colors.csv)",
    )
    parser.add_argument(
        "-o", "--output",
        default="color_scatter_3d.html",
        help="Output HTML file (default: color_scatter_3d.html)",
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=None,
        help="Maximum count for opacity scaling (default: average of top 5)",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading colors from: {args.input}")
    colors = load_colors_csv(args.input)
    print(f"Loaded {len(colors):,} unique colors")

    create_3d_scatter(colors, args.output, args.max_count)


if __name__ == "__main__":
    main()
