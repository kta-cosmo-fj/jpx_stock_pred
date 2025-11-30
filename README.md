# 📈 JPX Stock Analyzer

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**JPX Stock Analyzer** は、TOPIX 100 構成銘柄を対象に、ファンダメンタルズとモメンタムを自動分析し、投資有望銘柄を発掘するためのPythonツールです。
複雑な財務データを解析し、直感的な **HTMLレポート** として可視化します。
このアプリで被った損益に関して、製作者は一切責任を負いません。
投資は自己責任でお願いします。

---

## ✨ 主な機能 (Key Features)

*   **📊 自動データ収集**: `yfinance` を利用して、最新の株価・財務データを自動取得。
*   **🧮 総合スコアリング**: 成長性 (Growth)、収益性 (Efficiency)、割安性 (Valuation) の3つの観点から銘柄を多角的に評価。
*   **📈 モメンタム分析**: 過去の株価推移に基づき、短期〜中期のトレンドを数値化。
*   **🎨 ビジュアルレポート**: 分析結果をヒートマップ付きの美しいHTMLレポートで出力。ブラウザで手軽に確認可能。

---

## 🚀 インストール (Installation)

以下の手順で環境を構築してください。

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/jpx_stock_pred.git
cd jpx_stock_pred

# 依存ライブラリのインストール
pip install -r requirements.txt
```

---

## 💻 使い方 (Usage)

メインスクリプトを実行するだけで、分析からレポート作成まで自動で行われます。

```bash
python src/main.py
```

実行が完了すると、ディレクトリ直下に `report.html` が生成されます。このファイルをブラウザで開いて結果を確認してください。

---

## 📂 ディレクトリ構成 (Directory Structure)

```text
jpx_stock_pred/
├── src/
│   ├── main.py          # エントリーポイント
│   ├── data_manager.py  # データ取得・保存ロジック
│   ├── analyzer.py      # 分析・スコアリング計算
│   ├── visualizer.py    # HTMLレポート生成
│   └── config.py        # 設定ファイル
├── requirements.txt     # 依存ライブラリ
└── README.md            # ドキュメント
```

---

## 🧠 アルゴリズム詳細 (Technical Details)

本プロジェクトでは、TOPIX 100構成銘柄に対して独自のロジックで総合スコアを算出しています。

### 1. 基本的な考え方

各指標について、全銘柄の中での**パーセンタイル順位（0.0 ～ 1.0）**を計算し、その加重平均を総合スコアとしています。
相対評価であるため、市場環境全体の良し悪しに関わらず、比較対象の中で「相対的に割安・成長性が高い」銘柄が高スコアとなります。

### 2. 使用する指標と評価方向

以下の5つの指標を使用しています。

| 指標 | 内容 | 評価方向 | 理由 |
| :--- | :--- | :--- | :--- |
| **EPS成長率** | 1株当たり利益の成長率（過去3年） | **高いほど良い** | 利益成長は株価上昇の源泉であるため |
| **売上高成長率** | 売上高の成長率（過去3年） | **高いほど良い** | 事業規模の拡大を示すため |
| **ROE** | 自己資本利益率 | **高いほど良い** | 資本効率の良さを示すため |
| **PER** | 株価収益率 | **低いほど良い** | 割安度を測るため（低いほど割安） |
| **PBR** | 株価純資産倍率 | **低いほど良い** | 割安度を測るため（低いほど割安） |

※ PER、PBRについては、低いほど順位が高くなるように（1.0に近づくように）計算しています。

### 3. 総合スコアの計算式

各指標のスコア（$S_{metric}$）と重み（$W_{metric}$）を用いて、以下の式で算出します。

$$
\text{Score}_{\text{total}} = \frac{\sum (S_{metric} \times W_{metric})}{\sum W_{metric}}
$$

現在の設定（`src/config.py`）では、全ての指標の重みは **1.0** となっています。つまり、5つの指標の単純平均です。

### 4. モメンタムスコア（予測値）について

レポートに表示される「予測」は、機械学習による未来予測ではなく、**過去の特定期間における実績リターン（配当込み）**を示しています。これを「モメンタム（勢い）」の指標として参考にします。

計算式：
$$
\text{Momentum Score} = \frac{(\text{現在株価} - \text{過去株価}) + \text{期間中の配当合計}}{\text{過去株価}}
$$

期間は以下の4パターンで計算されます。
- 1日後（1 Day）
- 1ヶ月後（1 Month）
- 3ヶ月後（3 Months）
- 6ヶ月後（6 Months）

※ プラスであれば上昇トレンド（または配当による利益）、マイナスであれば下落トレンドを示唆します。
