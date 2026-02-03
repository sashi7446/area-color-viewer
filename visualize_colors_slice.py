#!/usr/bin/env python3
"""Hue slice visualization: L-C plane with interactive hue wheel selector."""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np


def srgb_to_linear(c: float) -> float:
    """Convert sRGB component (0-1) to linear RGB."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_srgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert linear sRGB to OKLab."""
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

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
    H = math.atan2(b, a)
    H_deg = math.degrees(H)
    if H_deg < 0:
        H_deg += 360
    return L, C, H_deg


def rgb_to_oklch(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB (0-255) to OKLCH."""
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    r_lin = srgb_to_linear(r_norm)
    g_lin = srgb_to_linear(g_norm)
    b_lin = srgb_to_linear(b_norm)

    L, a, b_val = linear_srgb_to_oklab(r_lin, g_lin, b_lin)
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


def generate_html(colors_oklch: list[dict],
                  bin_size: int, slice_width: float, output_path: str) -> None:
    """Generate self-contained HTML with wheel UI and scatter plot."""

    # Prepare scatter data as JSON
    scatter_data = []
    for c in colors_oklch:
        scatter_data.append({
            "L": round(c["L"], 4),
            "C": round(c["C"], 4),
            "H": round(c["H"], 2),
            "hex": c["Hex"],
            "count": c["Count"],
        })

    scatter_json = json.dumps(scatter_data)

    html_template = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hue Slice Viewer - L-C Plane</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #2c2a30;
            padding: 20px;
        }}
        .container {{
            display: flex;
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .wheel-panel {{
            background: #3a383e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .wheel-panel h2 {{
            margin-bottom: 15px;
            font-size: 16px;
            color: #e0e0e0;
        }}
        #wheelCanvas {{
            cursor: pointer;
        }}
        .hue-display {{
            margin-top: 15px;
            font-size: 24px;
            font-weight: 600;
            color: #e0e0e0;
        }}
        .hue-range {{
            font-size: 14px;
            color: #aaa;
            margin-top: 5px;
        }}
        .point-count {{
            font-size: 14px;
            color: #aaa;
            margin-top: 10px;
        }}
        .scatter-panel {{
            flex: 1;
            background: #3a383e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        .scatter-panel h2 {{
            margin-bottom: 15px;
            font-size: 16px;
            color: #e0e0e0;
        }}
        #scatterPlot {{
            width: 100%;
            height: 600px;
        }}
        .instructions {{
            margin-top: 15px;
            font-size: 12px;
            color: #888;
            text-align: center;
        }}
        .range-control {{
            margin-top: 15px;
            width: 100%;
            max-width: 300px;
        }}
        .range-control label {{
            display: block;
            font-size: 14px;
            color: #aaa;
            margin-bottom: 8px;
            text-align: center;
        }}
        .range-control input[type="range"] {{
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #555;
            outline: none;
            -webkit-appearance: none;
        }}
        .range-control input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #e0e0e0;
            cursor: pointer;
        }}
        .range-control input[type="range"]::-moz-range-thumb {{
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #e0e0e0;
            cursor: pointer;
            border: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="wheel-panel">
            <h2>Hue Selector (Color Wheel)</h2>
            <canvas id="wheelCanvas" width="400" height="400"></canvas>
            <div class="hue-display">H: <span id="hueValue">0.0</span>°</div>
            <div class="hue-range">Range: <span id="hueRange">350.0° - 10.0°</span></div>
            <div class="point-count">Points in slice: <span id="pointCount">0</span></div>
            <div class="range-control">
                <label>Slice Width: ±<span id="rangeValue">{slice_width:.0f}</span>°</label>
                <input type="range" id="rangeSlider" min="1" max="60" value="{slice_width:.0f}">
            </div>
            <div class="range-control">
                <label>Min Chroma: <span id="chromaValue">0.020</span></label>
                <input type="range" id="chromaSlider" min="0" max="20" value="4" step="1">
            </div>
            <div class="instructions">Drag on the wheel to select hue angle</div>
        </div>
        <div class="scatter-panel">
            <h2>L-C Plane (Lightness vs Chroma)</h2>
            <div id="scatterPlot"></div>
        </div>
    </div>

    <script>
        // Data from Python
        const scatterData = {scatter_json};
        const binSize = {bin_size};
        let sliceWidth = {slice_width};

        // State
        let currentHue = 0;
        let isDragging = false;

        // Range slider
        const rangeSlider = document.getElementById('rangeSlider');
        const rangeValue = document.getElementById('rangeValue');

        rangeSlider.addEventListener('input', (e) => {{
            sliceWidth = parseFloat(e.target.value);
            rangeValue.textContent = sliceWidth.toFixed(0);
            drawWheel();
            updateHueDisplay();
            updateScatterPlot();
        }});

        // Chroma threshold slider
        let minChroma = 0.02;
        const chromaSlider = document.getElementById('chromaSlider');
        const chromaValue = document.getElementById('chromaValue');

        chromaSlider.addEventListener('input', (e) => {{
            minChroma = parseFloat(e.target.value) * 0.005;
            chromaValue.textContent = minChroma.toFixed(3);
            drawWheel();
            updateScatterPlot();
        }});

        // Canvas setup
        const canvas = document.getElementById('wheelCanvas');
        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const outerRadius = 180;
        const innerRadius = 100;

        // Compute histogram dynamically based on minChroma
        function computeHistogram() {{
            const numBins = 360 / binSize;
            const hist = new Array(numBins).fill(0);
            for (const d of scatterData) {{
                if (d.C >= minChroma) {{
                    const binIdx = Math.floor(d.H / binSize) % numBins;
                    hist[binIdx] += d.count;
                }}
            }}
            return hist;
        }}

        // Convert hue to approximate RGB for display
        function hueToRgb(h) {{
            const s = 0.8, l = 0.5;
            const c = (1 - Math.abs(2 * l - 1)) * s;
            const x = c * (1 - Math.abs((h / 60) % 2 - 1));
            const m = l - c / 2;
            let r, g, b;
            if (h < 60) {{ r = c; g = x; b = 0; }}
            else if (h < 120) {{ r = x; g = c; b = 0; }}
            else if (h < 180) {{ r = 0; g = c; b = x; }}
            else if (h < 240) {{ r = 0; g = x; b = c; }}
            else if (h < 300) {{ r = x; g = 0; b = c; }}
            else {{ r = c; g = 0; b = x; }}
            return `rgb(${{Math.round((r + m) * 255)}}, ${{Math.round((g + m) * 255)}}, ${{Math.round((b + m) * 255)}})`;
        }}

        function drawWheel() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Compute histogram dynamically
            const currentHistogram = computeHistogram();
            const maxHist = Math.max(...currentHistogram, 1);

            // Draw histogram bars as radial segments
            const numBins = currentHistogram.length;
            const anglePerBin = (2 * Math.PI) / numBins;

            for (let i = 0; i < numBins; i++) {{
                const startAngle = (i * binSize - 90) * Math.PI / 180;
                const endAngle = ((i + 1) * binSize - 90) * Math.PI / 180;

                // Bar height based on histogram value
                const normalizedHeight = currentHistogram[i] / maxHist;
                const barRadius = innerRadius + (outerRadius - innerRadius) * normalizedHeight;

                // Color based on hue
                const hue = i * binSize + binSize / 2;
                ctx.fillStyle = hueToRgb(hue);
                ctx.globalAlpha = 0.6;

                ctx.beginPath();
                ctx.arc(centerX, centerY, barRadius, startAngle, endAngle);
                ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
                ctx.closePath();
                ctx.fill();
            }}

            ctx.globalAlpha = 1;

            // Draw inner circle (background)
            ctx.fillStyle = '#2c2a30';
            ctx.beginPath();
            ctx.arc(centerX, centerY, innerRadius - 2, 0, 2 * Math.PI);
            ctx.fill();

            // Draw outer ring
            ctx.strokeStyle = '#555';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(centerX, centerY, outerRadius, 0, 2 * Math.PI);
            ctx.stroke();

            // Draw slice indicator (fan shape)
            const startHue = currentHue - sliceWidth;
            const endHue = currentHue + sliceWidth;
            const startRad = (startHue - 90) * Math.PI / 180;
            const endRad = (endHue - 90) * Math.PI / 180;

            ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, outerRadius + 10, startRad, endRad);
            ctx.closePath();
            ctx.fill();

            // Draw current hue needle
            const needleAngle = (currentHue - 90) * Math.PI / 180;
            const needleLength = outerRadius + 15;

            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(
                centerX + needleLength * Math.cos(needleAngle),
                centerY + needleLength * Math.sin(needleAngle)
            );
            ctx.stroke();

            // Draw center dot
            ctx.fillStyle = '#e0e0e0';
            ctx.beginPath();
            ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI);
            ctx.fill();

            // Draw degree markers
            ctx.fillStyle = '#aaa';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            for (let deg = 0; deg < 360; deg += 30) {{
                const rad = (deg - 90) * Math.PI / 180;
                const textRadius = outerRadius + 25;
                const x = centerX + textRadius * Math.cos(rad);
                const y = centerY + textRadius * Math.sin(rad);
                ctx.fillText(deg + '°', x, y);
            }}
        }}

        function getAngleFromEvent(e) {{
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left - centerX;
            const y = e.clientY - rect.top - centerY;
            let angle = Math.atan2(y, x) * 180 / Math.PI + 90;
            if (angle < 0) angle += 360;
            return angle;
        }}

        // Circular distance considering 0-360 wrap
        function circularDistance(h1, h2) {{
            const diff = Math.abs(h1 - h2);
            return Math.min(diff, 360 - diff);
        }}

        function filterDataForHue(hue) {{
            return scatterData.filter(d =>
                d.C >= minChroma && circularDistance(d.H, hue) <= sliceWidth
            );
        }}

        function updateScatterPlot() {{
            const filtered = filterDataForHue(currentHue);

            // Update point count
            document.getElementById('pointCount').textContent = filtered.length.toLocaleString();

            // Calculate opacity based on count
            const counts = filtered.map(d => d.count);
            const maxCount = counts.length > 0 ? Math.max(...counts.slice(0, 100).sort((a, b) => b - a).slice(0, 5)) : 1;

            const trace = {{
                x: filtered.map(d => d.C),
                y: filtered.map(d => d.L),
                mode: 'markers',
                type: 'scatter',
                marker: {{
                    size: 6,
                    color: filtered.map(d => d.hex),
                    opacity: filtered.map(d => Math.min(Math.sqrt(d.count / maxCount), 1)),
                    line: {{
                        color: 'rgba(255,255,255,0.3)',
                        width: 0.5
                    }}
                }},
                text: filtered.map(d =>
                    `Hex: ${{d.hex}}<br>` +
                    `Count: ${{d.count.toLocaleString()}}<br>` +
                    `L: ${{d.L.toFixed(3)}}<br>` +
                    `C: ${{d.C.toFixed(3)}}<br>` +
                    `H: ${{d.H.toFixed(1)}}°`
                ),
                hoverinfo: 'text'
            }};

            const layout = {{
                xaxis: {{
                    title: {{ text: 'Chroma (C)', font: {{ color: '#aaa' }} }},
                    range: [0, 0.4],
                    gridcolor: '#444',
                    tickfont: {{ color: '#aaa' }},
                    linecolor: '#555'
                }},
                yaxis: {{
                    title: {{ text: 'Lightness (L)', font: {{ color: '#aaa' }} }},
                    range: [0, 1],
                    gridcolor: '#444',
                    tickfont: {{ color: '#aaa' }},
                    linecolor: '#555'
                }},
                margin: {{ t: 20, r: 20, b: 50, l: 60 }},
                paper_bgcolor: '#3a383e',
                plot_bgcolor: '#2c2a30',
                hovermode: 'closest'
            }};

            Plotly.react('scatterPlot', [trace], layout);
        }}

        function updateHueDisplay() {{
            document.getElementById('hueValue').textContent = currentHue.toFixed(1);

            let minHue = currentHue - sliceWidth;
            let maxHue = currentHue + sliceWidth;
            if (minHue < 0) minHue += 360;
            if (maxHue >= 360) maxHue -= 360;
            document.getElementById('hueRange').textContent =
                `${{minHue.toFixed(1)}}° - ${{maxHue.toFixed(1)}}°`;
        }}

        // Throttle function for performance
        function throttle(func, limit) {{
            let inThrottle;
            return function(...args) {{
                if (!inThrottle) {{
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }}
            }};
        }}

        const throttledUpdate = throttle(() => {{
            updateScatterPlot();
        }}, 50);

        // Event handlers
        canvas.addEventListener('mousedown', (e) => {{
            isDragging = true;
            currentHue = getAngleFromEvent(e);
            drawWheel();
            updateHueDisplay();
            throttledUpdate();
        }});

        canvas.addEventListener('mousemove', (e) => {{
            if (isDragging) {{
                currentHue = getAngleFromEvent(e);
                drawWheel();
                updateHueDisplay();
                throttledUpdate();
            }}
        }});

        canvas.addEventListener('mouseup', () => {{
            isDragging = false;
            updateScatterPlot(); // Final update without throttle
        }});

        canvas.addEventListener('mouseleave', () => {{
            if (isDragging) {{
                isDragging = false;
                updateScatterPlot();
            }}
        }});

        // Touch support
        canvas.addEventListener('touchstart', (e) => {{
            e.preventDefault();
            isDragging = true;
            const touch = e.touches[0];
            currentHue = getAngleFromEvent(touch);
            drawWheel();
            updateHueDisplay();
            throttledUpdate();
        }});

        canvas.addEventListener('touchmove', (e) => {{
            e.preventDefault();
            if (isDragging) {{
                const touch = e.touches[0];
                currentHue = getAngleFromEvent(touch);
                drawWheel();
                updateHueDisplay();
                throttledUpdate();
            }}
        }});

        canvas.addEventListener('touchend', () => {{
            isDragging = false;
            updateScatterPlot();
        }});

        // Initial render
        drawWheel();
        updateHueDisplay();
        updateScatterPlot();
    </script>
</body>
</html>
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)


def create_slice_viewer(colors: list[dict], output_path: str,
                        bin_size: int = 3, slice_width: float = 10.0) -> None:
    """Create hue slice viewer HTML."""

    # Convert to OKLCH (all colors, filtering done in browser)
    colors_oklch = []
    for color in colors:
        L, C, H = rgb_to_oklch(color["R"], color["G"], color["B"])
        colors_oklch.append({
            "L": L,
            "C": C,
            "H": H,
            "Hex": color["Hex"],
            "Count": color["Count"],
        })

    print(f"Converted {len(colors_oklch):,} colors to OKLCH")

    # Generate HTML
    generate_html(colors_oklch, bin_size, slice_width, output_path)
    print(f"Saved slice viewer to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create hue slice viewer for L-C plane visualization"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="dashboard_colors.csv",
        help="Input CSV file (default: dashboard_colors.csv)",
    )
    parser.add_argument(
        "-o", "--output",
        default="color_slice_viewer.html",
        help="Output HTML file (default: color_slice_viewer.html)",
    )
    parser.add_argument(
        "--bin-size",
        type=int,
        default=3,
        help="Histogram bin size in degrees (default: 3)",
    )
    parser.add_argument(
        "--slice-width",
        type=float,
        default=10.0,
        help="Slice half-width in degrees (default: 10.0, total width = 20°)",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading colors from: {args.input}")
    colors = load_colors_csv(args.input)
    print(f"Loaded {len(colors):,} unique colors")

    create_slice_viewer(colors, args.output, args.bin_size, args.slice_width)


if __name__ == "__main__":
    main()
