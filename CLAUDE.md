# Claude向けプロジェクトガイド

## コーディング規約

### 色変換は必ず color_utils.py を使え

from color_utils import rgb_to_oklch, load_colors_csv
わざわざファイルreadしないでいいようにドキュメントをここに書くよ！

**色変換:**
- `rgb_to_oklch(r:int, g:int, b:int) -> tuple[float, float, float]` - RGB(0-255) → OKLCH (L:0-1, C:0-0.4, H:0-360)
- `oklch_to_rgb(L:float, C:float, H:float) -> tuple[int, int, int]` - OKLCH → RGB(0-255)、sRGB色域外はクランプ
- `is_in_srgb_gamut(L:float, C:float, H:float, epsilon:float=1e-6) -> bool` - OKLCH色がsRGB色域内かを判定
- `rgb_to_hex(r:int, g:int, b:int) -> str` - RGB → "#RRGGBB"
- `hex_to_rgb(hex_str:str) -> tuple[int, int, int]` - "#RRGGBB" → (r, g, b)

**ファイルI/O:**
- `load_colors_csv(path:str) -> list[dict]` - CSVから色データを読み込み
{"Hex": row["Hex"], "R": int(row["R"]), "G": int(row["G"]), "B": int(row["B"]), "Count": int(row["Count"])}

- `save_colors_to_csv(colors:list[dict], path:str) -> None` - 色データをCSVに保存
csvのフォーマット
Hex,R,G,B,Count
#FF0000,255,0,0,1234

### 新しい処理を追加するときは必ず color_utils.py に追加せよ

実装する際は正確な情報源から検索しコピペせよ
https://bottosson.github.io/posts/oklab/　（計算式）

ユーティリティ関数は「3回以上使う処理」だけ抽出するのが鉄則やで。標準ライブラリやnumpy/pandasで1-2行で書けるものは要らない。無駄に関数増やすと管理コスト上がるだけだ。実際に同じコード3回書いた時点で初めてリファクタリングや。それまではコピペしろ。