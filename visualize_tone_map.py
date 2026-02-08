#!/usr/bin/env python3
"""OKLCH Tone Map: L-C plane with hue rings for color distribution analysis.

Displays color distribution in OKLCH space using a tone map layout
similar to PCCS. Y-axis = Lightness, X-axis = Chroma. Each cell contains
a ring of hue segments showing which hues exist at that L-C position.
"""

import argparse
import json
import sys
from pathlib import Path

from color_utils import load_colors_csv, rgb_to_oklch


def create_tone_map(colors: list[dict], output_path: str,
                    l_divs: int = 10, c_divs: int = 14) -> None:
    """Create OKLCH tone map HTML visualization.

    Args:
        colors: List of color dicts from load_colors_csv
        output_path: Path for output HTML file
        l_divs: Number of Lightness divisions (default 10)
        c_divs: Number of Chroma divisions (default 14)
    """
    colors_oklch = []
    for color in colors:
        L, C, H = rgb_to_oklch(color["R"], color["G"], color["B"])
        colors_oklch.append({
            "L": round(L, 4),
            "C": round(C, 4),
            "H": round(H, 2),
            "hex": color["Hex"],
            "count": color["Count"],
        })

    print(f"Converted {len(colors_oklch):,} colors to OKLCH")

    data_json = json.dumps(colors_oklch)
    html = _generate_html(data_json, l_divs, c_divs)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Saved tone map to: {output_path}")


def _generate_html(data_json: str, l_divs: int, c_divs: int) -> str:
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OKLCH Tone Map - L×C Distribution</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #2c2a30;
            color: #e0e0e0;
            padding: 20px;
        }}
        .header {{
            max-width: 1400px;
            margin: 0 auto 16px;
        }}
        .header h1 {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .controls {{
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            align-items: center;
            background: #3a383e;
            border-radius: 8px;
            padding: 12px 18px;
        }}
        .control-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .control-group label {{
            font-size: 13px;
            color: #aaa;
            white-space: nowrap;
        }}
        .control-group input[type="range"] {{
            width: 120px;
            height: 4px;
            border-radius: 2px;
            background: #555;
            outline: none;
            -webkit-appearance: none;
        }}
        .control-group input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #e0e0e0;
            cursor: pointer;
        }}
        .control-group input[type="range"]::-moz-range-thumb {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #e0e0e0;
            cursor: pointer;
            border: none;
        }}
        .control-value {{
            font-size: 13px;
            font-weight: 600;
            color: #e0e0e0;
            min-width: 24px;
            text-align: center;
        }}
        .canvas-wrap {{
            max-width: 1400px;
            margin: 0 auto;
            overflow: auto;
            background: #3a383e;
            border-radius: 12px;
            padding: 16px;
        }}
        #toneMap {{
            display: block;
        }}
        .tooltip {{
            position: fixed;
            pointer-events: none;
            background: rgba(30, 28, 34, 0.95);
            border: 1px solid #666;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            line-height: 1.6;
            color: #e0e0e0;
            display: none;
            z-index: 100;
            white-space: nowrap;
        }}
        .tooltip .swatch {{
            display: inline-block;
            width: 14px;
            height: 14px;
            border-radius: 3px;
            vertical-align: middle;
            margin-right: 6px;
            border: 1px solid rgba(255,255,255,0.3);
        }}
        .legend {{
            max-width: 1400px;
            margin: 12px auto 0;
            background: #3a383e;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 12px;
            color: #999;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .legend-swatch {{
            width: 20px;
            height: 14px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>OKLCH Tone Map — Lightness × Chroma Distribution</h1>
        <div class="controls">
            <div class="control-group">
                <label>L divisions:</label>
                <input type="range" id="lDivsSlider" min="4" max="20" value="{l_divs}">
                <span class="control-value" id="lDivsVal">{l_divs}</span>
            </div>
            <div class="control-group">
                <label>C divisions:</label>
                <input type="range" id="cDivsSlider" min="4" max="28" value="{c_divs}">
                <span class="control-value" id="cDivsVal">{c_divs}</span>
            </div>
            <div class="control-group">
                <label>Stats:</label>
                <span id="statsText" style="font-size:12px;color:#aaa;">—</span>
            </div>
        </div>
    </div>
    <div class="canvas-wrap">
        <canvas id="toneMap"></canvas>
    </div>
    <div class="legend">
        <div class="legend-item">
            <div class="legend-swatch" style="border:2px solid #888;background:transparent;"></div>
            <span>In-gamut, no data (border only)</span>
        </div>
        <div class="legend-item">
            <div class="legend-swatch" style="border:2px solid #c66;background:rgba(255,80,80,0.3);"></div>
            <span>Low count (faint fill)</span>
        </div>
        <div class="legend-item">
            <div class="legend-swatch" style="border:2px solid #c66;background:rgba(255,80,80,0.9);"></div>
            <span>High count (opaque fill)</span>
        </div>
        <div class="legend-item">
            <span style="color:#666;">Out-of-gamut → hidden</span>
        </div>
    </div>
    <div class="tooltip" id="tooltip"></div>

    <script>
        const colorData = {data_json};
        const H_BINS = 24;
        const C_MAX = 0.35;
        let lDivs = {l_divs};
        let cDivs = {c_divs};

        // ── Color conversion (OKLCH → sRGB) ──
        function oklchToRgb(L, C, H) {{
            const hRad = H * Math.PI / 180;
            const a = C * Math.cos(hRad);
            const b = C * Math.sin(hRad);

            const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
            const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
            const s_ = L - 0.0894841775 * a - 1.2914855480 * b;

            const l = l_ * l_ * l_;
            const m = m_ * m_ * m_;
            const s = s_ * s_ * s_;

            let rLin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s;
            let gLin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s;
            let bLin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s;

            function lin2srgb(c) {{
                return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
            }}

            const r = Math.round(Math.max(0, Math.min(255, lin2srgb(Math.max(0, Math.min(1, rLin))) * 255)));
            const g = Math.round(Math.max(0, Math.min(255, lin2srgb(Math.max(0, Math.min(1, gLin))) * 255)));
            const bv = Math.round(Math.max(0, Math.min(255, lin2srgb(Math.max(0, Math.min(1, bLin))) * 255)));
            return [r, g, bv];
        }}

        function isInSrgbGamut(L, C, H) {{
            const hRad = H * Math.PI / 180;
            const a = C * Math.cos(hRad);
            const b = C * Math.sin(hRad);

            const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
            const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
            const s_ = L - 0.0894841775 * a - 1.2914855480 * b;

            const l = l_ * l_ * l_;
            const m = m_ * m_ * m_;
            const s = s_ * s_ * s_;

            const rLin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s;
            const gLin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s;
            const bLin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s;

            const eps = 0.001;
            return rLin >= -eps && rLin <= 1 + eps &&
                   gLin >= -eps && gLin <= 1 + eps &&
                   bLin >= -eps && bLin <= 1 + eps;
        }}

        function maxGamutChroma(L, H) {{
            let lo = 0, hi = 0.4;
            for (let i = 0; i < 20; i++) {{
                const mid = (lo + hi) / 2;
                if (isInSrgbGamut(L, mid, H)) lo = mid;
                else hi = mid;
            }}
            return lo;
        }}

        // ── State ──
        let bins = {{}};
        let normCount = 1;
        let maxGamutCCache = {{}};
        // Store geometry for hit-testing
        let cellGeom = [];

        function binData() {{
            bins = {{}};
            const lStep = 1.0 / lDivs;
            const cStep = C_MAX / cDivs;
            const hStep = 360 / H_BINS;

            for (const d of colorData) {{
                if (d.C > C_MAX) continue;
                const li = Math.min(Math.floor(d.L / lStep), lDivs - 1);
                const ci = Math.min(Math.floor(d.C / cStep), cDivs - 1);
                if (li < 0 || ci < 0) continue;
                const hi = Math.floor(d.H / hStep) % H_BINS;

                const key = `${{li}}_${{ci}}_${{hi}}`;
                bins[key] = (bins[key] || 0) + d.count;
            }}

            // Normalization: average of top 10 bins
            const counts = Object.values(bins).sort((a, b) => b - a);
            if (counts.length >= 10) {{
                normCount = counts.slice(0, 10).reduce((a, b) => a + b, 0) / 10;
            }} else if (counts.length > 0) {{
                normCount = counts[0];
            }} else {{
                normCount = 1;
            }}
        }}

        function computeMaxGamutC() {{
            maxGamutCCache = {{}};
            const lStep = 1.0 / lDivs;
            const hStep = 360 / H_BINS;
            for (let li = 0; li < lDivs; li++) {{
                const Lc = (li + 0.5) * lStep;
                for (let hi = 0; hi < H_BINS; hi++) {{
                    const Hc = (hi + 0.5) * hStep;
                    maxGamutCCache[`${{li}}_${{hi}}`] = maxGamutChroma(Lc, Hc);
                }}
            }}
        }}

        // ── Canvas ──
        const canvas = document.getElementById('toneMap');
        const ctx = canvas.getContext('2d');
        const tooltipEl = document.getElementById('tooltip');
        const margin = {{ top: 20, right: 30, bottom: 50, left: 60 }};

        function updateCanvasSize() {{
            const targetCell = 70;
            canvas.width = margin.left + margin.right + cDivs * targetCell;
            canvas.height = margin.top + margin.bottom + lDivs * targetCell;
        }}

        // ── Rendering ──
        function render() {{
            updateCanvasSize();
            const W = canvas.width;
            const H = canvas.height;
            const plotW = W - margin.left - margin.right;
            const plotH = H - margin.top - margin.bottom;

            const cellW = plotW / cDivs;
            const cellH = plotH / lDivs;

            const lStep = 1.0 / lDivs;
            const cStep = C_MAX / cDivs;
            const hStep = 360 / H_BINS;
            const segAngle = 2 * Math.PI / H_BINS;

            ctx.fillStyle = '#2c2a30';
            ctx.fillRect(0, 0, W, H);

            // Grid lines
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
            ctx.lineWidth = 0.5;
            for (let li = 0; li <= lDivs; li++) {{
                const y = margin.top + (lDivs - li) * cellH;
                ctx.beginPath();
                ctx.moveTo(margin.left, y);
                ctx.lineTo(margin.left + plotW, y);
                ctx.stroke();
            }}
            for (let ci = 0; ci <= cDivs; ci++) {{
                const x = margin.left + ci * cellW;
                ctx.beginPath();
                ctx.moveTo(x, margin.top);
                ctx.lineTo(x, margin.top + plotH);
                ctx.stroke();
            }}

            // Reset geometry cache
            cellGeom = [];

            let totalBinsWithData = 0;
            let totalCount = 0;

            // Draw cells
            for (let li = 0; li < lDivs; li++) {{
                const Lc = (li + 0.5) * lStep;
                for (let ci = 0; ci < cDivs; ci++) {{
                    const Cc = (ci + 0.5) * cStep;

                    const cx = margin.left + ci * cellW + cellW / 2;
                    const cy = margin.top + (lDivs - 1 - li) * cellH + cellH / 2;

                    const rOuter = Math.min(cellW, cellH) * 0.44;
                    const rInner = rOuter * 0.38;

                    for (let hi = 0; hi < H_BINS; hi++) {{
                        const Hc = (hi + 0.5) * hStep;

                        if (!isInSrgbGamut(Lc, Cc, Hc)) continue;

                        const startAngle = hi * segAngle - Math.PI / 2;
                        const endAngle = (hi + 1) * segAngle - Math.PI / 2;

                        // Border: actual color at cell center
                        const borderRgb = oklchToRgb(Lc, Cc, Hc);

                        // Fill: high-chroma version
                        const mgc = maxGamutCCache[`${{li}}_${{hi}}`] || 0;
                        const fillC = Math.max(Cc, mgc * 0.8);
                        const fillRgb = oklchToRgb(Lc, fillC, Hc);

                        // Count → alpha
                        const key = `${{li}}_${{ci}}_${{hi}}`;
                        const count = bins[key] || 0;
                        const alpha = count > 0
                            ? Math.min(1, 0.12 + 0.88 * Math.sqrt(count / normCount))
                            : 0;

                        if (count > 0) {{
                            totalBinsWithData++;
                            totalCount += count;
                        }}

                        // Draw arc segment
                        ctx.beginPath();
                        ctx.arc(cx, cy, rOuter, startAngle, endAngle);
                        ctx.arc(cx, cy, rInner, endAngle, startAngle, true);
                        ctx.closePath();

                        // Fill
                        if (alpha > 0) {{
                            ctx.fillStyle = `rgba(${{fillRgb[0]}}, ${{fillRgb[1]}}, ${{fillRgb[2]}}, ${{alpha}})`;
                            ctx.fill();
                        }}

                        // Stroke
                        const borderAlpha = count > 0 ? 1.0 : 0.25;
                        ctx.strokeStyle = `rgba(${{borderRgb[0]}}, ${{borderRgb[1]}}, ${{borderRgb[2]}}, ${{borderAlpha}})`;
                        ctx.lineWidth = count > 0 ? 1.0 : 0.5;
                        ctx.stroke();

                        // Store geometry for hit-test
                        cellGeom.push({{
                            li, ci, hi, cx, cy, rOuter, rInner,
                            startAngle, endAngle, count,
                            Lc, Cc, Hc, borderRgb, fillRgb, alpha
                        }});
                    }}
                }}
            }}

            // Axes
            drawAxes(plotW, plotH, cellW, cellH, lStep, cStep);

            // Stats
            document.getElementById('statsText').textContent =
                `${{totalBinsWithData.toLocaleString()}} bins with data | ${{totalCount.toLocaleString()}} total pixels`;
        }}

        function drawAxes(plotW, plotH, cellW, cellH, lStep, cStep) {{
            ctx.fillStyle = '#999';
            ctx.font = '11px sans-serif';

            // Y-axis ticks (Lightness)
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            for (let li = 0; li < lDivs; li++) {{
                const Lc = (li + 0.5) * lStep;
                const y = margin.top + (lDivs - 1 - li) * cellH + cellH / 2;
                ctx.fillText(Lc.toFixed(2), margin.left - 6, y);
            }}

            // Y-axis title
            ctx.save();
            ctx.translate(14, margin.top + plotH / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.textAlign = 'center';
            ctx.font = '12px sans-serif';
            ctx.fillStyle = '#bbb';
            ctx.fillText('Lightness (L)', 0, 0);
            ctx.restore();

            // X-axis ticks (Chroma)
            ctx.fillStyle = '#999';
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            const skipX = cDivs > 18 ? 2 : 1;
            for (let ci = 0; ci < cDivs; ci++) {{
                if (skipX > 1 && ci % skipX !== 0) continue;
                const Cc = (ci + 0.5) * cStep;
                const x = margin.left + ci * cellW + cellW / 2;
                ctx.fillText(Cc.toFixed(3), x, margin.top + plotH + 5);
            }}

            // X-axis title
            ctx.fillStyle = '#bbb';
            ctx.font = '12px sans-serif';
            ctx.fillText('Chroma (C)', margin.left + plotW / 2, margin.top + plotH + 28);
        }}

        // ── Tooltip / Hit-testing ──
        function pointInArc(px, py, geom) {{
            const dx = px - geom.cx;
            const dy = py - geom.cy;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < geom.rInner || dist > geom.rOuter) return false;

            let angle = Math.atan2(dy, dx);
            // Normalize angles to compare
            let start = geom.startAngle;
            let end = geom.endAngle;

            // Normalize angle to [start, start + 2π)
            while (angle < start) angle += 2 * Math.PI;
            while (angle > start + 2 * Math.PI) angle -= 2 * Math.PI;

            return angle >= start && angle <= end;
        }}

        let hoveredGeom = null;

        canvas.addEventListener('mousemove', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const mx = (e.clientX - rect.left) * scaleX;
            const my = (e.clientY - rect.top) * scaleY;

            let found = null;
            for (const g of cellGeom) {{
                if (pointInArc(mx, my, g)) {{
                    found = g;
                    break;
                }}
            }}

            if (found) {{
                hoveredGeom = found;
                const lStep = 1.0 / lDivs;
                const cStep = C_MAX / cDivs;
                const hStep = 360 / H_BINS;

                const lLo = (found.li * lStep).toFixed(3);
                const lHi = ((found.li + 1) * lStep).toFixed(3);
                const cLo = (found.ci * cStep).toFixed(3);
                const cHi = ((found.ci + 1) * cStep).toFixed(3);
                const hLo = (found.hi * hStep).toFixed(1);
                const hHi = ((found.hi + 1) * hStep).toFixed(1);

                const rgb = found.borderRgb;
                const hex = `#${{rgb[0].toString(16).padStart(2,'0')}}${{rgb[1].toString(16).padStart(2,'0')}}${{rgb[2].toString(16).padStart(2,'0')}}`.toUpperCase();

                tooltipEl.innerHTML =
                    `<span class="swatch" style="background:rgb(${{rgb[0]}},${{rgb[1]}},${{rgb[2]}})"></span>` +
                    `<strong>${{hex}}</strong><br>` +
                    `L: ${{lLo}} – ${{lHi}}<br>` +
                    `C: ${{cLo}} – ${{cHi}}<br>` +
                    `H: ${{hLo}}° – ${{hHi}}°<br>` +
                    `<strong>Count: ${{found.count.toLocaleString()}}</strong>`;

                tooltipEl.style.display = 'block';
                tooltipEl.style.left = (e.clientX + 14) + 'px';
                tooltipEl.style.top = (e.clientY - 10) + 'px';

                // Keep tooltip in viewport
                const tr = tooltipEl.getBoundingClientRect();
                if (tr.right > window.innerWidth) {{
                    tooltipEl.style.left = (e.clientX - tr.width - 10) + 'px';
                }}
                if (tr.bottom > window.innerHeight) {{
                    tooltipEl.style.top = (e.clientY - tr.height - 10) + 'px';
                }}
            }} else {{
                hoveredGeom = null;
                tooltipEl.style.display = 'none';
            }}
        }});

        canvas.addEventListener('mouseleave', () => {{
            hoveredGeom = null;
            tooltipEl.style.display = 'none';
        }});

        // ── Slider handlers ──
        const lSlider = document.getElementById('lDivsSlider');
        const cSlider = document.getElementById('cDivsSlider');
        const lVal = document.getElementById('lDivsVal');
        const cVal = document.getElementById('cDivsVal');

        function onSliderChange() {{
            lDivs = parseInt(lSlider.value);
            cDivs = parseInt(cSlider.value);
            lVal.textContent = lDivs;
            cVal.textContent = cDivs;
            computeMaxGamutC();
            binData();
            render();
        }}

        lSlider.addEventListener('input', onSliderChange);
        cSlider.addEventListener('input', onSliderChange);

        // ── Init ──
        computeMaxGamutC();
        binData();
        render();
    </script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(
        description="Create OKLCH tone map (L-C plane with hue rings)"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="dashboard_colors.csv",
        help="Input CSV file (default: dashboard_colors.csv)",
    )
    parser.add_argument(
        "-o", "--output",
        default="oklch_tone_map.html",
        help="Output HTML file (default: oklch_tone_map.html)",
    )
    parser.add_argument(
        "--l-divs",
        type=int,
        default=10,
        help="Initial Lightness divisions (default: 10)",
    )
    parser.add_argument(
        "--c-divs",
        type=int,
        default=14,
        help="Initial Chroma divisions (default: 14, step=0.025)",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading colors from: {args.input}")
    colors = load_colors_csv(args.input)
    print(f"Loaded {len(colors):,} unique colors")

    create_tone_map(colors, args.output, args.l_divs, args.c_divs)


if __name__ == "__main__":
    main()
