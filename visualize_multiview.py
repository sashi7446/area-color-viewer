#!/usr/bin/env python3
"""Multi-view synchronized OKLCH color space viewer with brushing & linking.

Generates a standalone HTML file with 4 synchronized views:
  - 3D OKLCH space (rotatable/zoomable)
  - L-C plane (front view)
  - C-H plane (top view, pseudo-polar)
  - L-H plane (side view)

Interactive features:
  - Brushing & linking across all views
  - Hover synchronization with crosshair markers
  - Click-to-focus with neighborhood zoom
  - Dynamic L/C/H range filtering
  - Voxel mode with adjustable granularity
  - Heatmap density visualization
  - Voxel statistics on hover
"""

import argparse
import json
import sys
from pathlib import Path

from color_utils import load_colors_csv, rgb_to_oklch


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OKLCH Multi-View Color Explorer</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,monospace;background:#1e1c21;color:#e0e0e0;overflow:hidden;height:100vh}
.app{display:flex;flex-direction:column;height:100vh}

/* --- Toolbar --- */
.toolbar{display:flex;align-items:center;gap:16px;padding:8px 16px;background:#2a2830;border-bottom:1px solid #3a3840;flex-wrap:wrap;min-height:48px}
.toolbar-section{display:flex;align-items:center;gap:8px}
.toolbar-section label{font-size:11px;color:#aaa;white-space:nowrap}
.toolbar-divider{width:1px;height:28px;background:#3a3840}

/* Dual range */
.dual-range{position:relative;width:120px;height:20px}
.dual-range input[type=range]{position:absolute;width:100%;top:2px;-webkit-appearance:none;background:none;pointer-events:none;margin:0;height:16px}
.dual-range input[type=range]::-webkit-slider-runnable-track{height:4px;background:#444;border-radius:2px}
.dual-range input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:#c0c0c0;cursor:pointer;pointer-events:all;margin-top:-4px}
.dual-range input[type=range]::-moz-range-track{height:4px;background:#444;border-radius:2px;border:none}
.dual-range input[type=range]::-moz-range-thumb{width:12px;height:12px;border-radius:50%;background:#c0c0c0;cursor:pointer;pointer-events:all;border:none}
.filter-val{font-size:11px;color:#ccc;font-variant-numeric:tabular-nums;min-width:80px;display:inline-block;text-align:center}

/* Single range */
.single-range{width:100px}
.single-range input[type=range]{width:100%;-webkit-appearance:none;height:4px;background:#444;border-radius:2px;outline:none}
.single-range input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:#c0c0c0;cursor:pointer}
.single-range input[type=range]::-moz-range-thumb{width:12px;height:12px;border-radius:50%;background:#c0c0c0;cursor:pointer;border:none}

/* Buttons */
.btn{padding:3px 10px;border:1px solid #555;background:#333;color:#ccc;border-radius:4px;font-size:11px;cursor:pointer;transition:background .15s}
.btn:hover{background:#444}
.btn.active{background:#5a4fcf;border-color:#7a6fef;color:#fff}

/* --- Views Grid --- */
.views-grid{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:4px;flex:1;padding:4px;min-height:0}
.view-panel{background:#2a2830;border-radius:6px;overflow:hidden;display:flex;flex-direction:column;min-height:0}
.view-header{padding:4px 10px;font-size:11px;color:#999;background:#252330;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}
.view-header span{font-weight:600;color:#bbb}
.view-container{flex:1;min-height:0}
.view-container>div{width:100%!important;height:100%!important}

/* --- Info Panel --- */
.info-bar{display:flex;align-items:center;gap:16px;padding:6px 16px;background:#2a2830;border-top:1px solid #3a3840;min-height:36px;font-size:11px}
.info-swatch{width:24px;height:24px;border-radius:4px;border:1px solid #555;flex-shrink:0}
.info-detail{color:#ccc;font-variant-numeric:tabular-nums}
.info-detail b{color:#fff;margin-right:4px}
.selection-info{margin-left:auto;color:#aaa}
.voxel-tooltip{position:fixed;background:#333;border:1px solid #555;border-radius:6px;padding:8px 12px;font-size:11px;color:#ddd;pointer-events:none;z-index:1000;display:none;max-width:260px;box-shadow:0 4px 12px rgba(0,0,0,.5)}
.voxel-tooltip .vt-swatch{width:20px;height:20px;border-radius:3px;border:1px solid #666;display:inline-block;vertical-align:middle;margin-right:6px}
.hue-legend{display:flex;gap:0;height:8px;border-radius:3px;overflow:hidden;flex:1;max-width:240px;margin:0 8px;border:1px solid #3a3840}
.hue-legend div{flex:1;min-width:0;cursor:pointer;position:relative}
.hue-legend div:hover::after{content:attr(data-hue);position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:#222;color:#ccc;font-size:9px;padding:1px 4px;border-radius:2px;white-space:nowrap;pointer-events:none;margin-bottom:2px}

/* --- Responsive: Tablet (<=900px) --- */
@media(max-width:900px){
  .toolbar{gap:8px;padding:6px 10px;overflow-x:auto;-webkit-overflow-scrolling:touch;flex-wrap:nowrap;scrollbar-width:thin}
  .toolbar-divider{display:none}
  .toolbar-section{flex-shrink:0}
  .dual-range{width:90px}
  .filter-val{min-width:60px;font-size:10px}
  .single-range{width:70px}
  .views-grid{grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr}
}

/* --- Responsive: Mobile (<=600px) --- */
@media(max-width:600px){
  body{overflow:auto;height:auto}
  .app{height:auto;min-height:100vh;min-height:100dvh}
  .toolbar{gap:6px;padding:6px 8px;min-height:40px;overflow-x:auto;-webkit-overflow-scrolling:touch;flex-wrap:nowrap;scrollbar-width:thin}
  .toolbar::-webkit-scrollbar{height:3px}
  .toolbar::-webkit-scrollbar-thumb{background:#555;border-radius:2px}
  .toolbar-section{flex-shrink:0}
  .toolbar-section label{font-size:10px}
  .toolbar-divider{display:none}
  .dual-range{width:70px}
  .filter-val{min-width:50px;font-size:9px}
  .single-range{width:60px}
  .btn{padding:5px 12px;font-size:12px;min-height:32px;touch-action:manipulation}
  /* Larger touch targets for sliders */
  .dual-range input[type=range]::-webkit-slider-thumb{width:18px;height:18px;margin-top:-7px}
  .dual-range input[type=range]::-moz-range-thumb{width:18px;height:18px}
  .single-range input[type=range]::-webkit-slider-thumb{width:18px;height:18px}
  .single-range input[type=range]::-moz-range-thumb{width:18px;height:18px}
  /* Single column grid with fixed-height panels */
  .views-grid{grid-template-columns:1fr;grid-template-rows:repeat(4,300px);gap:2px;padding:2px;flex:none}
  .view-panel{min-height:0}
  .view-header{padding:3px 8px;font-size:10px}
  .view-header span{font-size:10px}
  .hue-legend{max-width:120px;height:6px}
  /* Info bar */
  .info-bar{gap:8px;padding:6px 10px;font-size:10px;flex-wrap:wrap;position:sticky;bottom:0;z-index:10;min-height:32px}
  .info-swatch{width:20px;height:20px}
  .selection-info{margin-left:0;width:100%}
  .voxel-tooltip{font-size:10px;max-width:200px}
}

/* --- Responsive: Small mobile (<=400px) --- */
@media(max-width:400px){
  .views-grid{grid-template-rows:repeat(4,260px)}
  .dual-range{width:55px}
  .filter-val{min-width:40px;font-size:8px}
  .btn{padding:4px 8px;font-size:11px}
}
</style>
</head>
<body>
<div class="app">

<!-- Toolbar -->
<div class="toolbar">
  <div class="toolbar-section">
    <label>L:</label>
    <span class="filter-val" id="fL-val">0.00 — 1.00</span>
    <div class="dual-range">
      <input type="range" id="fL-min" min="0" max="1000" value="0">
      <input type="range" id="fL-max" min="0" max="1000" value="1000">
    </div>
  </div>
  <div class="toolbar-section">
    <label>C:</label>
    <span class="filter-val" id="fC-val">0.00 — 0.40</span>
    <div class="dual-range">
      <input type="range" id="fC-min" min="0" max="1000" value="0">
      <input type="range" id="fC-max" min="0" max="1000" value="1000">
    </div>
  </div>
  <div class="toolbar-section">
    <label>H:</label>
    <span class="filter-val" id="fH-val">0° — 360°</span>
    <div class="dual-range">
      <input type="range" id="fH-min" min="0" max="1000" value="0">
      <input type="range" id="fH-max" min="0" max="1000" value="1000">
    </div>
  </div>
  <div class="toolbar-divider"></div>
  <div class="toolbar-section">
    <label>Voxel:</label>
    <div class="single-range">
      <input type="range" id="voxelSlider" min="3" max="40" value="12">
    </div>
    <span class="filter-val" id="voxelVal">12 bins</span>
  </div>
  <div class="toolbar-section">
    <button class="btn" id="btnPoints" onclick="setMode('points')">Points</button>
    <button class="btn active" id="btnBoth" onclick="setMode('both')">Both</button>
    <button class="btn" id="btnVoxels" onclick="setMode('voxels')">Voxels</button>
  </div>
  <div class="toolbar-divider"></div>
  <div class="toolbar-section">
    <label>Density ≥</label>
    <div class="single-range">
      <input type="range" id="densitySlider" min="0" max="1000" value="0">
    </div>
    <span class="filter-val" id="densityVal">0</span>
  </div>
  <button class="btn" id="btnReset" onclick="resetAll()">Reset</button>
</div>

<!-- 4-Pane Grid -->
<div class="views-grid">
  <div class="view-panel">
    <div class="view-header"><span>3D OKLCH Space</span><span id="stat3d"></span></div>
    <div class="view-container"><div id="view3d"></div></div>
  </div>
  <div class="view-panel">
    <div class="view-header"><span>L — C Plane (Front View)</span><div class="hue-legend" id="hueLegend"></div><span id="statLC"></span></div>
    <div class="view-container"><div id="viewLC"></div></div>
  </div>
  <div class="view-panel">
    <div class="view-header"><span>C — H Plane (Top View)</span><span id="statCH"></span></div>
    <div class="view-container"><div id="viewCH"></div></div>
  </div>
  <div class="view-panel">
    <div class="view-header"><span>L — H Plane (Side View)</span><span id="statLH"></span></div>
    <div class="view-container"><div id="viewLH"></div></div>
  </div>
</div>

<!-- Info Bar -->
<div class="info-bar">
  <div class="info-swatch" id="infoSwatch" style="background:#333"></div>
  <div class="info-detail" id="infoText">Hover over a point for details</div>
  <div class="selection-info" id="selInfo"></div>
</div>

</div>

<!-- Voxel Tooltip -->
<div class="voxel-tooltip" id="voxelTip"></div>

<script>
// ================================================================
// DATA
// ================================================================
const RAW = /*__DATA__*/[];

const pts = RAW.map((d, i) => {
  const hRad = d.H * Math.PI / 180;
  return {
    i, L: d.L, C: d.C, H: d.H,
    hex: d.hex, count: d.count,
    r: d.r, g: d.g, b: d.b,
    cx: d.C * Math.cos(hRad),
    cy: d.C * Math.sin(hRad),
  };
});

// Precompute vivid "pure hue" border color for each point.
// Uses L=0.7, C=0.2 in OKLCH — high chroma for clear hue identification.
// Out-of-gamut values are clamped, preserving dominant hue.
const hueHexCache = pts.map(d => {
  const rgb = oklchToRgb(0.7, 0.2, d.H);
  return rgbHex(rgb[0], rgb[1], rgb[2]);
});

// ================================================================
// STATE
// ================================================================
let selected = new Set();
let focusIdx = -1;
let filterL = [0, 1], filterC = [0, 0.4], filterH = [0, 360];
let voxelBins = 12;
let showMode = 'both'; // 'points' | 'voxels' | 'both'
let densityThreshold = 0;
let filtered = [];  // indices into pts
let voxels = [];
let hoverGuard = false;
let pendingRender = false;

const VIEW_IDS = ['view3d', 'viewLC', 'viewCH', 'viewLH'];
const VIEW_2D = ['viewLC', 'viewCH', 'viewLH'];

// ================================================================
// COLOR CONVERSION (JS)
// ================================================================
function oklchToRgb(L, C, H) {
  const hR = H * Math.PI / 180;
  const a = C * Math.cos(hR), b = C * Math.sin(hR);
  const l_ = L + 0.3963377774*a + 0.2158037573*b;
  const m_ = L - 0.1055613458*a - 0.0638541728*b;
  const s_ = L - 0.0894841775*a - 1.2914855480*b;
  const l=l_*l_*l_, m=m_*m_*m_, s=s_*s_*s_;
  let rL = 4.0767416621*l - 3.3077115913*m + 0.2309699292*s;
  let gL = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s;
  let bL = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s;
  function g2s(c){c=Math.max(0,Math.min(1,c));return c<=.0031308?12.92*c:1.055*Math.pow(c,1/2.4)-.055}
  return [Math.round(g2s(rL)*255), Math.round(g2s(gL)*255), Math.round(g2s(bL)*255)];
}
function rgbHex(r,g,b){return '#'+[r,g,b].map(x=>Math.max(0,Math.min(255,x)).toString(16).padStart(2,'0')).join('').toUpperCase()}

// ================================================================
// FILTERING
// ================================================================
function hueInRange(h, lo, hi) {
  if (lo <= hi) return h >= lo && h <= hi;
  return h >= lo || h <= hi;
}

function applyFilters() {
  filtered = [];
  for (let i = 0; i < pts.length; i++) {
    const d = pts[i];
    if (d.L >= filterL[0] && d.L <= filterL[1] &&
        d.C >= filterC[0] && d.C <= filterC[1] &&
        hueInRange(d.H, filterH[0], filterH[1])) {
      filtered.push(i);
    }
  }
}

// ================================================================
// VOXELIZATION
// ================================================================
function computeVoxels() {
  const nB = voxelBins;
  const sL = 1.0/nB, sC = 0.4/nB, sH = 360.0/nB;
  const map = new Map();

  for (const idx of filtered) {
    const d = pts[idx];
    const kl = Math.min(Math.floor(d.L / sL), nB-1);
    const kc = Math.min(Math.floor(d.C / sC), nB-1);
    const kh = Math.min(Math.floor(d.H / sH), nB-1);
    const key = kl*10000 + kc*100 + kh;
    if (!map.has(key)) {
      map.set(key, {
        sL:0,sC:0,sHx:0,sHy:0,tot:0,n:0,pts:[],
        sL2:0,sC2:0,
        cL:(kl+.5)*sL, cC:(kc+.5)*sC, cH:(kh+.5)*sH,
      });
    }
    const v = map.get(key);
    v.sL += d.L*d.count; v.sC += d.C*d.count;
    v.sHx += Math.cos(d.H*Math.PI/180)*d.count;
    v.sHy += Math.sin(d.H*Math.PI/180)*d.count;
    v.tot += d.count; v.n++;
    v.pts.push(idx);
    v.sL2 += d.L*d.L*d.count;
    v.sC2 += d.C*d.C*d.count;
  }

  voxels = [];
  for (const [, v] of map) {
    if (v.tot < densityThreshold) continue;
    const aL = v.sL/v.tot, aC = v.sC/v.tot;
    let aH = Math.atan2(v.sHy, v.sHx)*180/Math.PI;
    if (aH < 0) aH += 360;
    const stdL = Math.sqrt(Math.max(0, v.sL2/v.tot - aL*aL));
    const stdC = Math.sqrt(Math.max(0, v.sC2/v.tot - aC*aC));
    const rgb = oklchToRgb(aL, aC, aH);
    const hRad = aH * Math.PI / 180;
    voxels.push({
      L:aL, C:aC, H:aH, tot:v.tot, n:v.n, pts:v.pts,
      stdL, stdC,
      hex: rgbHex(rgb[0],rgb[1],rgb[2]),
      r:rgb[0], g:rgb[1], b:rgb[2],
      cx: aC*Math.cos(hRad), cy: aC*Math.sin(hRad),
      cL:v.cL, cC:v.cC, cH:v.cH,
    });
  }
  voxels.sort((a,b) => a.tot - b.tot); // draw dense on top
}

// ================================================================
// MARKER HELPERS
// ================================================================
function ptColors(indices, sel) {
  const hasSel = sel.size > 0;
  return indices.map(i => {
    const d = pts[i];
    if (!hasSel || sel.has(i)) return d.hex;
    return 'rgba('+d.r+','+d.g+','+d.b+',0.06)';
  });
}
function ptSizes(indices, sel, base, hi) {
  const hasSel = sel.size > 0;
  return indices.map(i => hasSel && sel.has(i) ? hi : base);
}
function ptOpacities(indices, sel) {
  const hasSel = sel.size > 0;
  return indices.map(i => (!hasSel || sel.has(i)) ? 1.0 : 0.08);
}
function ptBorderColors(indices, sel) {
  const hasSel = sel.size > 0;
  return indices.map(i => {
    if (hasSel && !sel.has(i)) return 'rgba(80,80,80,0.12)';
    return hueHexCache[i];
  });
}

function voxelSizes() {
  if (voxels.length === 0) return [];
  const mx = Math.max(...voxels.map(v=>v.tot));
  return voxels.map(v => 4 + 20 * Math.sqrt(v.tot / mx));
}
function voxelBorderColors() {
  return voxels.map(v => {
    const rgb = oklchToRgb(0.7, 0.2, v.H);
    return rgbHex(rgb[0], rgb[1], rgb[2]);
  });
}

// ================================================================
// HOVER TEXT
// ================================================================
function ptHoverText(indices) {
  return indices.map(i => {
    const d = pts[i];
    return d.hex+'<br>L:'+d.L.toFixed(3)+' C:'+d.C.toFixed(3)+' H:'+d.H.toFixed(1)+
           '°<br>Pixels:'+d.count.toLocaleString();
  });
}
function voxelHoverText() {
  return voxels.map(v =>
    v.hex+'<br>Avg L:'+v.L.toFixed(3)+' C:'+v.C.toFixed(3)+' H:'+v.H.toFixed(1)+
    '°<br>Pixels:'+v.tot.toLocaleString()+' ('+v.n+' colors)'+
    '<br>σL:'+v.stdL.toFixed(3)+' σC:'+v.stdC.toFixed(3)
  );
}

// ================================================================
// BUILD TRACES
// ================================================================
function buildTraces3d() {
  const traces = [];
  const showPts = showMode === 'points' || showMode === 'both';
  const showVox = showMode === 'voxels' || showMode === 'both';

  if (showPts) {
    traces.push({
      type:'scatter3d', mode:'markers', name:'Points',
      x: filtered.map(i=>pts[i].cx),
      y: filtered.map(i=>pts[i].cy),
      z: filtered.map(i=>pts[i].L),
      marker:{size:2.5, color:ptColors(filtered,selected), opacity:0.85,
              line:{color:ptBorderColors(filtered,selected), width:0.5}},
      text: ptHoverText(filtered),
      hoverinfo:'text', customdata: filtered,
    });
  }
  if (showVox && voxels.length > 0) {
    traces.push({
      type:'scatter3d', mode:'markers', name:'Voxels',
      x: voxels.map(v=>v.cx), y: voxels.map(v=>v.cy), z: voxels.map(v=>v.L),
      marker:{size:voxelSizes(), color:voxels.map(v=>v.hex), opacity:0.6,
              line:{color:voxelBorderColors(), width:0.8}},
      text: voxelHoverText(),
      hoverinfo:'text',
    });
  }
  // Crosshair trace (always last)
  traces.push({
    type:'scatter3d', mode:'markers', name:'_xhair',
    x:[], y:[], z:[],
    marker:{size:10, color:'rgba(255,255,80,0.9)', symbol:'diamond',
            line:{color:'#fff', width:1.5}},
    hoverinfo:'skip', showlegend:false,
  });
  return traces;
}

function buildTracesLC() {
  const traces = [];
  const showPts = showMode === 'points' || showMode === 'both';
  const showVox = showMode === 'voxels' || showMode === 'both';

  if (showPts) {
    traces.push({
      type:'scattergl', mode:'markers', name:'Points',
      x: filtered.map(i=>pts[i].C),
      y: filtered.map(i=>pts[i].L),
      marker:{size:4, color:ptColors(filtered,selected),
              line:{color:ptBorderColors(filtered,selected), width:1.0}},
      text: ptHoverText(filtered),
      hoverinfo:'text', customdata: filtered,
      selected:{marker:{opacity:1}}, unselected:{marker:{opacity:0.08}},
    });
  }
  if (showVox && voxels.length > 0) {
    traces.push({
      type:'scattergl', mode:'markers', name:'Voxels',
      x: voxels.map(v=>v.C), y: voxels.map(v=>v.L),
      marker:{size:voxelSizes(), color:voxels.map(v=>v.hex), opacity:0.55,
              line:{color:voxelBorderColors(), width:0.8}},
      text: voxelHoverText(), hoverinfo:'text',
    });
  }
  // Crosshair
  traces.push({
    type:'scattergl', mode:'markers', name:'_xhair',
    x:[], y:[],
    marker:{size:12, color:'rgba(255,255,80,0.9)', symbol:'cross',
            line:{color:'#fff', width:1.5}},
    hoverinfo:'skip', showlegend:false,
  });
  return traces;
}

function buildTracesCH() {
  const traces = [];
  const showPts = showMode === 'points' || showMode === 'both';
  const showVox = showMode === 'voxels' || showMode === 'both';

  if (showPts) {
    traces.push({
      type:'scattergl', mode:'markers', name:'Points',
      x: filtered.map(i=>pts[i].cx),
      y: filtered.map(i=>pts[i].cy),
      marker:{size:4, color:ptColors(filtered,selected),
              line:{color:ptBorderColors(filtered,selected), width:1.0}},
      text: ptHoverText(filtered),
      hoverinfo:'text', customdata: filtered,
      selected:{marker:{opacity:1}}, unselected:{marker:{opacity:0.08}},
    });
  }
  if (showVox && voxels.length > 0) {
    traces.push({
      type:'scattergl', mode:'markers', name:'Voxels',
      x: voxels.map(v=>v.cx), y: voxels.map(v=>v.cy),
      marker:{size:voxelSizes(), color:voxels.map(v=>v.hex), opacity:0.55,
              line:{color:voxelBorderColors(), width:0.8}},
      text: voxelHoverText(), hoverinfo:'text',
    });
  }
  // Crosshair
  traces.push({
    type:'scattergl', mode:'markers', name:'_xhair',
    x:[], y:[],
    marker:{size:12, color:'rgba(255,255,80,0.9)', symbol:'cross',
            line:{color:'#fff', width:1.5}},
    hoverinfo:'skip', showlegend:false,
  });
  return traces;
}

function buildTracesLH() {
  const traces = [];
  const showPts = showMode === 'points' || showMode === 'both';
  const showVox = showMode === 'voxels' || showMode === 'both';

  if (showPts) {
    traces.push({
      type:'scattergl', mode:'markers', name:'Points',
      x: filtered.map(i=>pts[i].H),
      y: filtered.map(i=>pts[i].L),
      marker:{size:4, color:ptColors(filtered,selected),
              line:{color:ptBorderColors(filtered,selected), width:1.0}},
      text: ptHoverText(filtered),
      hoverinfo:'text', customdata: filtered,
      selected:{marker:{opacity:1}}, unselected:{marker:{opacity:0.08}},
    });
  }
  if (showVox && voxels.length > 0) {
    traces.push({
      type:'scattergl', mode:'markers', name:'Voxels',
      x: voxels.map(v=>v.H), y: voxels.map(v=>v.L),
      marker:{size:voxelSizes(), color:voxels.map(v=>v.hex), opacity:0.55,
              line:{color:voxelBorderColors(), width:0.8}},
      text: voxelHoverText(), hoverinfo:'text',
    });
  }
  // Crosshair
  traces.push({
    type:'scattergl', mode:'markers', name:'_xhair',
    x:[], y:[],
    marker:{size:12, color:'rgba(255,255,80,0.9)', symbol:'cross',
            line:{color:'#fff', width:1.5}},
    hoverinfo:'skip', showlegend:false,
  });
  return traces;
}

// ================================================================
// POLAR GRID SHAPES & ANNOTATIONS for C-H view
// ================================================================
function polarShapes() {
  const shapes = [];
  // Circles at C = 0.1, 0.2, 0.3
  for (const r of [0.1, 0.2, 0.3]) {
    shapes.push({type:'circle', x0:-r, y0:-r, x1:r, y1:r,
      line:{color:'#3a3840', width:1}, layer:'below'});
  }
  // Radial lines every 30 degrees
  for (let deg = 0; deg < 360; deg += 30) {
    const rad = deg * Math.PI / 180;
    const r = 0.35;
    shapes.push({type:'line', x0:0, y0:0,
      x1:r*Math.cos(rad), y1:r*Math.sin(rad),
      line:{color:'#3a3840', width:1, dash:'dot'}, layer:'below'});
  }
  return shapes;
}
function polarAnnotations() {
  const anns = [];
  for (let deg = 0; deg < 360; deg += 30) {
    const rad = deg * Math.PI / 180;
    const r = 0.37;
    anns.push({x:r*Math.cos(rad), y:r*Math.sin(rad),
      text:deg+'°', showarrow:false, font:{color:'#666', size:9}});
  }
  // Radial labels
  for (const rv of [0.1, 0.2, 0.3]) {
    anns.push({x:rv+0.01, y:0.01, text:rv.toFixed(1), showarrow:false,
      font:{color:'#555', size:8}});
  }
  return anns;
}

// ================================================================
// LAYOUTS
// ================================================================
const darkAxis = {gridcolor:'#333', zerolinecolor:'#444', tickfont:{color:'#999',size:9},
                  titlefont:{color:'#aaa',size:10}, linecolor:'#444'};
const darkBg = {paper_bgcolor:'#2a2830', plot_bgcolor:'#1e1c21'};

function layout3d() {
  const m = isMobile();
  return {
    ...darkBg,
    margin:{l:0,r:0,b:0,t:0},
    scene:{
      xaxis:{title:m?'':'C·cos(H)', range:[-.4,.4], ...darkAxis},
      yaxis:{title:m?'':'C·sin(H)', range:[-.4,.4], ...darkAxis},
      zaxis:{title:m?'L':'Lightness (L)', range:[0,1], ...darkAxis},
      aspectmode:'manual', aspectratio:{x:1,y:1,z:1.3},
      camera:{eye:{x:1.6,y:1.6,z:0.9}, up:{x:0,y:0,z:1}},
      bgcolor:'#1e1c21',
    },
    showlegend:false,
    hovermode:'closest',
  };
}
function layoutLC() {
  const m = isMobile();
  return {
    ...darkBg,
    margin:m?{l:36,r:6,b:30,t:4}:{l:44,r:10,b:36,t:6},
    xaxis:{title:m?'C':'Chroma (C)', range:[0,0.4], ...darkAxis},
    yaxis:{title:m?'L':'Lightness (L)', range:[0,1], ...darkAxis},
    showlegend:false, hovermode:'closest', dragmode:'select',
  };
}
function layoutCH() {
  const m = isMobile();
  return {
    ...darkBg,
    margin:m?{l:30,r:6,b:30,t:4}:{l:36,r:10,b:36,t:6},
    xaxis:{title:m?'':'C·cos(H)', range:[-.4,.4], ...darkAxis, scaleanchor:'y', scaleratio:1},
    yaxis:{title:m?'':'C·sin(H)', range:[-.4,.4], ...darkAxis},
    shapes: polarShapes(),
    annotations: polarAnnotations(),
    showlegend:false, hovermode:'closest', dragmode:'select',
  };
}
function layoutLH() {
  const m = isMobile();
  return {
    ...darkBg,
    margin:m?{l:36,r:6,b:30,t:4}:{l:44,r:10,b:36,t:6},
    xaxis:{title:m?'H°':'Hue (H°)', range:[0,360], dtick:m?90:60, ...darkAxis},
    yaxis:{title:m?'L':'Lightness (L)', range:[0,1], ...darkAxis},
    showlegend:false, hovermode:'closest', dragmode:'select',
  };
}

// ================================================================
// RENDER
// ================================================================
function renderAll() {
  if (pendingRender) return;
  pendingRender = true;
  requestAnimationFrame(() => {
    pendingRender = false;
    _doRender();
  });
}

function isMobile() { return window.innerWidth <= 600; }

function plotConfig() {
  const cfg = {displayModeBar: true, responsive: true, displaylogo: false,
    modeBarButtonsToRemove: ['sendDataToCloud','lasso2d']};
  if (isMobile()) {
    cfg.displayModeBar = false;
    cfg.scrollZoom = false;
  }
  return cfg;
}

function _doRender() {
  applyFilters();
  computeVoxels();

  const cfg = plotConfig();
  Plotly.react('view3d', buildTraces3d(), layout3d(), cfg);
  Plotly.react('viewLC', buildTracesLC(), layoutLC(), cfg);
  Plotly.react('viewCH', buildTracesCH(), layoutCH(), cfg);
  Plotly.react('viewLH', buildTracesLH(), layoutLH(), cfg);

  attachEvents();
  updateStats();
}

function updateStats() {
  document.getElementById('stat3d').textContent = filtered.length.toLocaleString() + ' pts';
  document.getElementById('statLC').textContent = filtered.length.toLocaleString() + ' pts';
  document.getElementById('statCH').textContent = filtered.length.toLocaleString() + ' pts';
  document.getElementById('statLH').textContent = filtered.length.toLocaleString() + ' pts';
  if (showMode !== 'points' && voxels.length > 0) {
    document.getElementById('stat3d').textContent += ' / ' + voxels.length + ' vox';
  }
}

// ================================================================
// HIGHLIGHT UPDATE (efficient restyle)
// ================================================================
function updateHighlight() {
  const colors = ptColors(filtered, selected);
  const borderColors = ptBorderColors(filtered, selected);
  const showPts = showMode === 'points' || showMode === 'both';
  if (!showPts) return;

  try {
    Plotly.restyle('view3d', {'marker.color':[colors], 'marker.line.color':[borderColors]}, [0]);
    Plotly.restyle('viewLC', {'marker.color':[colors], 'marker.line.color':[borderColors]}, [0]);
    Plotly.restyle('viewCH', {'marker.color':[colors], 'marker.line.color':[borderColors]}, [0]);
    Plotly.restyle('viewLH', {'marker.color':[colors], 'marker.line.color':[borderColors]}, [0]);
  } catch(e) {}

  // Selection info
  if (selected.size > 0) {
    let totalPx = 0;
    for (const i of selected) totalPx += pts[i].count;
    document.getElementById('selInfo').textContent =
      selected.size.toLocaleString() + ' selected | ' + totalPx.toLocaleString() + ' px';
  } else {
    document.getElementById('selInfo').textContent = '';
  }
}

// ================================================================
// CROSSHAIR (hover sync via dedicated trace)
// ================================================================
function showCrosshair(d) {
  const xhairIdx3d = getXhairIdx('view3d');
  const xhairIdxLC = getXhairIdx('viewLC');
  const xhairIdxCH = getXhairIdx('viewCH');
  const xhairIdxLH = getXhairIdx('viewLH');
  try {
    Plotly.restyle('view3d', {x:[[d.cx]], y:[[d.cy]], z:[[d.L]]}, [xhairIdx3d]);
    Plotly.restyle('viewLC', {x:[[d.C]], y:[[d.L]]}, [xhairIdxLC]);
    Plotly.restyle('viewCH', {x:[[d.cx]], y:[[d.cy]]}, [xhairIdxCH]);
    Plotly.restyle('viewLH', {x:[[d.H]], y:[[d.L]]}, [xhairIdxLH]);
  } catch(e) {}
}

function hideCrosshair() {
  const ids = ['view3d','viewLC','viewCH','viewLH'];
  for (const id of ids) {
    const idx = getXhairIdx(id);
    try {
      if (id === 'view3d') Plotly.restyle(id, {x:[[]], y:[[]], z:[[]]}, [idx]);
      else Plotly.restyle(id, {x:[[]], y:[[]]}, [idx]);
    } catch(e) {}
  }
}

function getXhairIdx(viewId) {
  // Crosshair trace is always the last trace
  const el = document.getElementById(viewId);
  return el.data ? el.data.length - 1 : 0;
}

// ================================================================
// INFO PANEL
// ================================================================
function showPointInfo(d) {
  document.getElementById('infoSwatch').style.background = d.hex;
  document.getElementById('infoText').innerHTML =
    '<b>' + d.hex + '</b> &nbsp; ' +
    'L:<b>' + d.L.toFixed(3) + '</b> C:<b>' + d.C.toFixed(3) +
    '</b> H:<b>' + d.H.toFixed(1) + '°</b> &nbsp; ' +
    'RGB(' + d.r + ',' + d.g + ',' + d.b + ') &nbsp; ' +
    'Pixels:<b>' + d.count.toLocaleString() + '</b>';
}

function showVoxelInfo(v, evt) {
  const tip = document.getElementById('voxelTip');
  tip.innerHTML =
    '<span class="vt-swatch" style="background:'+v.hex+'"></span>' +
    '<b>Voxel</b><br>' +
    'Avg L: '+v.L.toFixed(3)+' C: '+v.C.toFixed(3)+' H: '+v.H.toFixed(1)+'°<br>'+
    'Total pixels: '+v.tot.toLocaleString()+'<br>'+
    'Unique colors: '+v.n+'<br>'+
    'σL: '+v.stdL.toFixed(4)+' σC: '+v.stdC.toFixed(4);
  tip.style.display = 'block';
  tip.style.left = (evt.event.clientX + 12) + 'px';
  tip.style.top = (evt.event.clientY - 10) + 'px';
}

function hideVoxelTip() {
  document.getElementById('voxelTip').style.display = 'none';
}

// ================================================================
// EVENTS
// ================================================================
let _eventsAttached = {};

function attachEvents() {
  for (const vid of VIEW_IDS) {
    const el = document.getElementById(vid);
    // Remove old listeners by re-attaching (Plotly removes on react)
    if (_eventsAttached[vid]) continue;
    _eventsAttached[vid] = true;

    // Hover
    el.on('plotly_hover', function(ev) {
      if (hoverGuard) return;
      hoverGuard = true;
      const pt = ev.points[0];
      const traceIdx = pt.curveNumber;
      const traceData = el.data[traceIdx];

      if (traceData.name === 'Points' && traceData.customdata) {
        const globalIdx = traceData.customdata[pt.pointNumber];
        const d = pts[globalIdx];
        showPointInfo(d);
        showCrosshair(d);
      } else if (traceData.name === 'Voxels') {
        const v = voxels[pt.pointNumber];
        if (v) {
          showVoxelInfo(v, ev);
          showCrosshair(v);
          document.getElementById('infoSwatch').style.background = v.hex;
          document.getElementById('infoText').innerHTML =
            '<b>Voxel '+v.hex+'</b> &nbsp; Avg L:'+v.L.toFixed(3)+
            ' C:'+v.C.toFixed(3)+' H:'+v.H.toFixed(1)+'° &nbsp; '+
            v.tot.toLocaleString()+' px ('+v.n+' colors)';
        }
      }
      requestAnimationFrame(() => { hoverGuard = false; });
    });

    el.on('plotly_unhover', function() {
      if (hoverGuard) return;
      hoverGuard = true;
      hideCrosshair();
      hideVoxelTip();
      requestAnimationFrame(() => { hoverGuard = false; });
    });

    // Selection (2D only)
    if (VIEW_2D.includes(vid)) {
      el.on('plotly_selected', function(ev) {
        if (!ev || !ev.points) { selected.clear(); updateHighlight(); return; }
        selected.clear();
        for (const pt of ev.points) {
          const traceData = el.data[pt.curveNumber];
          if (traceData.name === 'Points' && traceData.customdata) {
            selected.add(traceData.customdata[pt.pointNumber]);
          } else if (traceData.name === 'Voxels') {
            // Select all points in voxel
            const v = voxels[pt.pointNumber];
            if (v) for (const pi of v.pts) selected.add(pi);
          }
        }
        updateHighlight();

        // Focus if single point
        if (selected.size === 1) {
          const idx = [...selected][0];
          focusOnPoint(idx);
        }
      });

      el.on('plotly_deselect', function() {
        selected.clear();
        updateHighlight();
      });
    }

    // Click (all views)
    el.on('plotly_click', function(ev) {
      const pt = ev.points[0];
      const traceData = el.data[pt.curveNumber];
      if (traceData.name === 'Points' && traceData.customdata) {
        const globalIdx = traceData.customdata[pt.pointNumber];
        focusOnPoint(globalIdx);
      } else if (traceData.name === 'Voxels') {
        const v = voxels[pt.pointNumber];
        if (v) drillIntoVoxel(v);
      }
    });
  }
}

// ================================================================
// FOCUS / ZOOM
// ================================================================
function focusOnPoint(idx) {
  focusIdx = idx;
  const d = pts[idx];
  showPointInfo(d);
  showCrosshair(d);

  // Highlight neighborhood
  const radius = 0.08;
  selected.clear();
  for (const fi of filtered) {
    const p = pts[fi];
    const dL = p.L - d.L;
    const dC = p.C - d.C;
    const dHnorm = Math.min(Math.abs(p.H - d.H), 360 - Math.abs(p.H - d.H)) / 360;
    const dist = Math.sqrt(dL*dL + dC*dC + dHnorm*dHnorm);
    if (dist <= radius) selected.add(fi);
  }
  updateHighlight();

  // Zoom 2D views
  const mC = 0.06, mL = 0.12, mH = 40;
  try {
    Plotly.relayout('viewLC', {
      'xaxis.range': [Math.max(0, d.C-mC), Math.min(0.4, d.C+mC)],
      'yaxis.range': [Math.max(0, d.L-mL), Math.min(1, d.L+mL)],
    });
    const chR = Math.max(0.05, d.C + 0.05);
    Plotly.relayout('viewCH', {
      'xaxis.range': [d.cx - chR, d.cx + chR],
      'yaxis.range': [d.cy - chR, d.cy + chR],
    });
    Plotly.relayout('viewLH', {
      'xaxis.range': [d.H - mH, d.H + mH],
      'yaxis.range': [Math.max(0, d.L-mL), Math.min(1, d.L+mL)],
    });
  } catch(e) {}
}

// ================================================================
// VOXEL DRILL-DOWN
// ================================================================
function drillIntoVoxel(v) {
  // Temporarily filter to only show this voxel's points
  selected.clear();
  for (const pi of v.pts) selected.add(pi);
  updateHighlight();

  // Zoom to voxel's region
  const mC = 0.04, mL = 0.08, mH = 25;
  try {
    Plotly.relayout('viewLC', {
      'xaxis.range': [Math.max(0, v.C-mC), Math.min(0.4, v.C+mC)],
      'yaxis.range': [Math.max(0, v.L-mL), Math.min(1, v.L+mL)],
    });
    Plotly.relayout('viewLH', {
      'xaxis.range': [v.H - mH, v.H + mH],
      'yaxis.range': [Math.max(0, v.L-mL), Math.min(1, v.L+mL)],
    });
  } catch(e) {}
}

// ================================================================
// FILTER CONTROLS
// ================================================================
function setupFilters() {
  setupDualRange('fL-min','fL-max','fL-val', 1.0, v => v.toFixed(2),
    (lo,hi) => { filterL = [lo,hi]; renderAll(); });
  setupDualRange('fC-min','fC-max','fC-val', 0.4, v => v.toFixed(2),
    (lo,hi) => { filterC = [lo,hi]; renderAll(); });
  setupDualRange('fH-min','fH-max','fH-val', 360, v => v.toFixed(0)+'°',
    (lo,hi) => { filterH = [lo,hi]; renderAll(); });

  // Voxel size
  const vs = document.getElementById('voxelSlider');
  const vv = document.getElementById('voxelVal');
  vs.addEventListener('input', () => {
    voxelBins = parseInt(vs.value);
    vv.textContent = voxelBins + ' bins';
    renderAll();
  });

  // Density threshold
  const ds = document.getElementById('densitySlider');
  const dv = document.getElementById('densityVal');
  ds.addEventListener('input', () => {
    // Map 0-1000 to exponential scale
    const v = parseInt(ds.value);
    if (v === 0) { densityThreshold = 0; }
    else {
      const maxCount = pts.length > 0 ? Math.max(...pts.map(p=>p.count)) : 1;
      densityThreshold = Math.round(Math.pow(v / 1000, 2) * maxCount);
    }
    dv.textContent = densityThreshold.toLocaleString();
    renderAll();
  });
}

function setupDualRange(minId, maxId, valId, scale, fmt, onChange) {
  const minEl = document.getElementById(minId);
  const maxEl = document.getElementById(maxId);
  const valEl = document.getElementById(valId);

  function update() {
    let lo = parseInt(minEl.value);
    let hi = parseInt(maxEl.value);
    if (lo > hi) { [lo, hi] = [hi, lo]; minEl.value = lo; maxEl.value = hi; }
    const loV = lo * scale / 1000;
    const hiV = hi * scale / 1000;
    valEl.textContent = fmt(loV) + ' — ' + fmt(hiV);
    onChange(loV, hiV);
  }

  minEl.addEventListener('input', update);
  maxEl.addEventListener('input', update);
}

// ================================================================
// MODE & RESET
// ================================================================
function setMode(mode) {
  showMode = mode;
  document.getElementById('btnPoints').classList.toggle('active', mode === 'points');
  document.getElementById('btnBoth').classList.toggle('active', mode === 'both');
  document.getElementById('btnVoxels').classList.toggle('active', mode === 'voxels');
  renderAll();
}

function resetAll() {
  selected.clear(); focusIdx = -1;
  filterL = [0,1]; filterC = [0,0.4]; filterH = [0,360];
  document.getElementById('fL-min').value = 0;
  document.getElementById('fL-max').value = 1000;
  document.getElementById('fC-min').value = 0;
  document.getElementById('fC-max').value = 1000;
  document.getElementById('fH-min').value = 0;
  document.getElementById('fH-max').value = 1000;
  document.getElementById('fL-val').textContent = '0.00 — 1.00';
  document.getElementById('fC-val').textContent = '0.00 — 0.40';
  document.getElementById('fH-val').textContent = '0° — 360°';
  document.getElementById('selInfo').textContent = '';
  document.getElementById('infoText').textContent = 'Hover over a point for details';
  document.getElementById('infoSwatch').style.background = '#333';
  _eventsAttached = {};
  renderAll();

  // Reset zoom on 2D views
  setTimeout(() => {
    try {
      Plotly.relayout('viewLC', {'xaxis.autorange':true,'yaxis.autorange':true});
      Plotly.relayout('viewCH', {'xaxis.autorange':true,'yaxis.autorange':true});
      Plotly.relayout('viewLH', {'xaxis.autorange':true,'yaxis.autorange':true});
    } catch(e) {}
  }, 100);
}

// ================================================================
// RESIZE
// ================================================================
function handleResize() {
  for (const vid of VIEW_IDS) {
    const el = document.getElementById(vid);
    if (el && el.data) {
      Plotly.Plots.resize(el);
    }
  }
}
window.addEventListener('resize', () => {
  clearTimeout(window._resizeTimer);
  window._resizeTimer = setTimeout(handleResize, 150);
});
// Also handle orientation change on mobile
window.addEventListener('orientationchange', () => {
  clearTimeout(window._resizeTimer);
  window._resizeTimer = setTimeout(handleResize, 300);
});
// Handle visualViewport resize (mobile address bar show/hide)
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    clearTimeout(window._resizeTimer);
    window._resizeTimer = setTimeout(handleResize, 150);
  });
}

// ================================================================
// HUE LEGEND
// ================================================================
function buildHueLegend() {
  const el = document.getElementById('hueLegend');
  if (!el) return;
  for (let h = 0; h < 360; h += 10) {
    const seg = document.createElement('div');
    const rgb = oklchToRgb(0.7, 0.2, h + 5);
    seg.style.background = rgbHex(rgb[0], rgb[1], rgb[2]);
    seg.setAttribute('data-hue', h + '°');
    el.appendChild(seg);
  }
}

// ================================================================
// INIT
// ================================================================
function init() {
  buildHueLegend();
  setupFilters();
  renderAll();
}

init();
</script>
</body>
</html>"""


def create_multiview(colors: list[dict], output_path: str) -> None:
    """Create multi-view OKLCH viewer HTML."""
    data = []
    for c in colors:
        L, C, H = rgb_to_oklch(c["R"], c["G"], c["B"])
        data.append({
            "L": round(L, 4),
            "C": round(C, 4),
            "H": round(H, 2),
            "hex": c["Hex"],
            "count": c["Count"],
            "r": c["R"],
            "g": c["G"],
            "b": c["B"],
        })

    data_json = json.dumps(data, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("/*__DATA__*/[]", data_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Saved multi-view explorer to: {output_path}")
    print(f"Total colors: {len(data):,}")


def main():
    parser = argparse.ArgumentParser(
        description="Create multi-view synchronized OKLCH color space viewer"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="dashboard_colors.csv",
        help="Input CSV file (default: dashboard_colors.csv)",
    )
    parser.add_argument(
        "-o", "--output",
        default="oklch_multiview.html",
        help="Output HTML file (default: oklch_multiview.html)",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading colors from: {args.input}")
    colors = load_colors_csv(args.input)
    print(f"Loaded {len(colors):,} unique colors")

    create_multiview(colors, args.output)


if __name__ == "__main__":
    main()
