#!/usr/bin/env python3
"""Unified CLI for color visualization: image -> 3D scatter plot HTML."""

import argparse
import sys
from pathlib import Path

from extract_colors import get_colors_from_image
from visualize_colors_3d import create_3d_scatter


def process_image(image_path: str, output_path: str | None = None, max_count: int = 60000) -> str:
    """Process a single image to generate 3D scatter plot HTML.

    Args:
        image_path: Path to input image
        output_path: Path to output HTML (auto-generated if None)
        max_count: Maximum count for opacity scaling

    Returns:
        Path to generated HTML file
    """
    image_path = Path(image_path)

    # Auto-generate output path: IMG_123.JPG -> IMG_123_scatter_3d.html
    if output_path is None:
        output_path = image_path.stem + "_scatter_3d.html"

    print(f"\n=== {image_path.name} ===")

    # Extract colors directly to memory (no intermediate CSV)
    colors = get_colors_from_image(str(image_path))
    print(f"抽出完了: {len(colors):,} 色")

    # Generate 3D scatter plot
    create_3d_scatter(colors, str(output_path), max_count)

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3D color scatter plots from images",
        epilog="Example: python viz.py *.JPG"
    )
    parser.add_argument(
        "images",
        nargs="+",
        help="Input image(s) - supports multiple files and glob patterns"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output HTML path (only for single image; ignored for multiple)"
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=60000,
        help="Maximum count for opacity scaling (default: 60000)"
    )
    args = parser.parse_args()

    # Validate input files
    valid_images = []
    for image_path in args.images:
        if not Path(image_path).exists():
            print(f"Warning: {image_path} not found, skipping", file=sys.stderr)
        else:
            valid_images.append(image_path)

    if not valid_images:
        print("Error: No valid images found", file=sys.stderr)
        sys.exit(1)

    # Process images
    output_files = []
    for i, image_path in enumerate(valid_images):
        # Only use custom output for single image
        output_path = args.output if len(valid_images) == 1 else None
        result = process_image(image_path, output_path, args.max_count)
        output_files.append(result)

    # Summary
    print(f"\n=== 完了 ===")
    print(f"処理画像数: {len(output_files)}")
    for path in output_files:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
