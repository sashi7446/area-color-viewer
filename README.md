# area-color-viewer
ピクセルノイズがある画像から、人間が遠目から見た「平された色」を抽出したいときに使えます。
スポイトツールで何度もクリックする代わりに、OKLCH色空間で色相、彩度、明度を見ながら納得できる色選びを可能にします。

- [3D散布図を見る](https://sashi7446.github.io/area-color-viewer/color_scatter_3d.html) - OKLCH色空間での色分布を3D表示
- [色相スライスビューアを見る](https://sashi7446.github.io/area-color-viewer/color_slice_viewer.html) - 色相ごとの色を分析
- [マルチビューエクスプローラを見る](https://sashi7446.github.io/area-color-viewer/oklch_multiview.html) - 4ペイン同期ビューでインタラクティブ分析

## マルチビューエクスプローラ

4つの同期ビューでOKLCH色空間をインタラクティブに探索できます。

| ペイン | ビュー | 説明 |
|--------|--------|------|
| 左上 | 3D OKLCH空間 | 回転・ズーム可能な3D散布図 |
| 右上 | L-C平面（正面図） | 明度 vs 彩度 |
| 左下 | C-H平面（上面図） | 彩度 vs 色相（擬似極座標） |
| 右下 | L-H平面（側面図） | 明度 vs 色相 |

**インタラクティブ機能:**
- **ブラッシング＆リンキング** — 任意の2Dビューで矩形選択すると、全ビューで対応点がハイライト
- **ホバー同期** — どのビューでもホバーするとクロスヘアが全ビュー連動、L/C/H値・RGB見本を表示
- **クリックでフォーカス** — クリックした点の近傍にズーム＆周辺色をハイライト
- **動的フィルタリング** — L/C/Hのデュアルレンジスライダーでリアルタイム絞り込み
- **ボクセル可視化** — 粒度調整スライダーで密度ヒートマップ表示、ボクセルクリックでドリルダウン
- **統計ツールチップ** — ボクセルホバーで平均L/C/H、ピクセル数、色数、標準偏差を表示

## プロジェクト構成

```
├── extract_colors.py          # 画像から色を抽出してCSV出力
├── visualize_colors_3d.py     # OKLCH空間での3D散布図を生成
├── visualize_colors_slice.py  # 色相スライスビューアを生成
├── visualize_multiview.py     # マルチビュー同期エクスプローラを生成
├── color_utils.py             # 共通ユーティリティ（色変換、ファイルI/O）
└── color-extractor/           # Claude Code skill
```

## 使い方

```bash
# 1. 画像から色を抽出
python extract_colors.py image.png -o colors.csv

# 2. 3D散布図を生成
python visualize_colors_3d.py colors.csv -o scatter.html

# 3. 色相スライスビューアを生成
python visualize_colors_slice.py colors.csv -o slice.html

# 4. マルチビュー同期エクスプローラを生成
python visualize_multiview.py colors.csv -o multiview.html
```

## 共通ユーティリティ (color_utils.py)

色変換やファイルI/Oは `color_utils.py` に集約されています。

**色変換:**
- `rgb_to_oklch(r, g, b)` - RGB(0-255) → OKLCH (L:0-1, C:0-0.4, H:0-360)
- `oklch_to_rgb(L, C, H)` - OKLCH → RGB(0-255)、sRGB色域外はクランプ
- `is_in_srgb_gamut(L, C, H)` - OKLCH色がsRGB色域内かを判定
- `rgb_to_hex(r, g, b)` - RGB → "#RRGGBB"
- `hex_to_rgb(hex_str)` - "#RRGGBB" → (r, g, b)

**ファイルI/O:**
- `load_colors_csv(path)` - CSVから色データを読み込み
- `save_colors_to_csv(colors, path)` - 色データをCSVに保存
