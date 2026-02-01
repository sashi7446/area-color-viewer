---
name: color-extractor
description: Extract all unique color codes (HEX) from an image and output as CSV with occurrence counts. Use when user wants to analyze colors in an image, extract color palette, count pixel colors, or export color data to CSV/spreadsheet format. Triggers on requests like "extract colors from image", "get color codes", "analyze image colors", "color palette extraction".
---

# Color Extractor

Extract all unique HEX color codes from an image and output as CSV.

## Usage

```bash
python scripts/extract_colors.py <image_path> [-o output.csv]
```

## Features

- Resizes large images to ~500,000 pixels using nearest neighbor interpolation (preserves original colors, no artifacts)
- Outputs HEX codes with occurrence counts, sorted by frequency
- Shows progress during extraction

## Output Format

CSV with columns: `Hex`, `R`, `G`, `B`, `Count`

```csv
Hex,R,G,B,Count
#FFFFFF,255,255,255,12345
#000000,0,0,0,6789
...
```

## Dependencies

- Pillow (`pip install Pillow --break-system-packages`)