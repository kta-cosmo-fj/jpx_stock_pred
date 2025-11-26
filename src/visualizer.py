import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from . import config

class Visualizer:
    def __init__(self):
        self.output_dir = config.OUTPUT_DIR
        # 日本語フォントの動的設定
        self.font_prop = self._find_japanese_font()

    def _find_japanese_font(self):
        """
        利用可能な日本語フォントを探す
        """
        font_candidates = [
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc",
            "C:\\Windows\\Fonts\\yugothr.ttc",  # Yu Gothic Regular
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", # Linux (example)
            "/System/Library/Fonts/Hiragino Sans GB.ttc" # Mac (example)
        ]
        
        for path in font_candidates:
            if os.path.exists(path):
                print(f"Using font: {path}")
                return fm.FontProperties(fname=path)
        
        # フォールバック: システムのデフォルト
        print("Warning: No Japanese font found. Using default.")
        return None

    def plot_scores(self, df, top_n=20):
        """
        総合スコアの上位銘柄を棒グラフで表示・保存
        """
        df_top = df.head(top_n).sort_values("score_total", ascending=True)
        
        plt.figure(figsize=(10, 8))
        plt.barh(df_top["ticker"], df_top["score_total"], color="skyblue")
        plt.xlabel("Total Score (Percentile Rank)")
        plt.title(f"Top {top_n} Stocks by Fundamental Score")
        plt.grid(axis="x", linestyle="--", alpha=0.7)
        
        # フォント適用
        if self.font_prop:
            plt.yticks(fontproperties=self.font_prop)
        
        output_path = os.path.join(self.output_dir, "top_scores.png")
        plt.savefig(output_path, bbox_inches="tight")
        plt.close()
        print(f"スコアチャートを保存しました: {output_path}")

    def generate_html_report(self, df_scores, df_returns, top_n=20):
        """
        分析結果をHTMLレポートとして出力（みんかぶリンク付き）
        """
        # スコア上位の銘柄にリターン情報を結合
        # df_scores: ticker, score_total, ...
        # df_returns: SecuritiesCode, momentum_score_1month, ...
        
        # カラム名の統一
        df_scores = df_scores.rename(columns={"ticker": "code"})
        df_returns = df_returns.rename(columns={"SecuritiesCode": "code"})
        
        # 結合
        merged = pd.merge(df_scores, df_returns, on="code", how="left")
        merged = merged.head(top_n)
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>TOPIX 100 分析レポート</title>
            <style>
                body {{ 
                    font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif; 
                    margin: 0;
                    padding: 20px;
                    background-color: #f4f7f6;
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: #fff;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ 
                    color: #2c3e50; 
                    border-bottom: 2px solid #eee; 
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                p.meta {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 30px; }}
                
                .chart-container {{
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 20px;
                    background: #fafafa;
                    border-radius: 8px;
                }}
                
                table {{ 
                    border-collapse: collapse; 
                    width: 100%; 
                    margin-top: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                th, td {{ 
                    padding: 12px 15px; 
                    text-align: left; 
                    border-bottom: 1px solid #e0e0e0;
                }}
                th {{ 
                    background-color: #34495e; 
                    color: #fff; 
                    font-weight: 600;
                    white-space: nowrap;
                }}
                tr:hover {{ background-color: #f5f5f5; }}
                
                .positive {{ color: #27ae60; font-weight: bold; }}
                .negative {{ color: #c0392b; font-weight: bold; }}
                .neutral {{ color: #7f8c8d; }}
                
                .score-cell {{ font-weight: bold; color: #2980b9; }}
                
                .link-btn {{ 
                    display: inline-block;
                    background-color: #3498db; 
                    color: white; 
                    padding: 6px 12px; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    font-size: 0.85em;
                    transition: background-color 0.2s;
                }}
                .link-btn:hover {{ background-color: #2980b9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>TOPIX 100 分析レポート</h1>
                <p class="meta">作成日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="chart-container">
                    <img src="top_scores.png" alt="Score Chart" style="max-width: 100%; height: auto; border: 1px solid #eee;">
                </div>
                
                <h2>総合スコア上位 {top_n} 銘柄</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>順位</th>
                                <th>コード</th>
                                <th>総合スコア</th>
                                <th>EPS成長率</th>
                                <th>売上高成長率</th>
                                <th>PER</th>
                                <th>PBR</th>
                                <th>ROE</th>
                                <th>1日後<br>予測</th>
                                <th>1ヶ月後<br>予測</th>
                                <th>3ヶ月後<br>予測</th>
                                <th>6ヶ月後<br>予測</th>
                                <th>リンク</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for i, row in merged.iterrows():
            code_str = str(row['code']).replace('.T', '')
            minkabu_url = f"https://minkabu.jp/stock/{code_str}"
            
            # フォーマット
            score = f"{row['score_total']:.2f}"
            eps = f"{row['eps_growth']:.2%}" if pd.notnull(row['eps_growth']) else "-"
            rev = f"{row['revenue_growth']:.2%}" if pd.notnull(row['revenue_growth']) else "-"
            per = f"{row['per']:.2f}" if pd.notnull(row['per']) else "-"
            pbr = f"{row['pbr']:.2f}" if pd.notnull(row['pbr']) else "-"
            roe = f"{row['roe']:.2f}" if pd.notnull(row['roe']) else "-"
            
            # 予測（モメンタムスコア）の処理
            def format_pred(val):
                if pd.isnull(val):
                    return "-", "neutral"
                cls = "positive" if val > 0 else "negative"
                return f"{val:.2%}", cls

            pred_1d_str, pred_1d_cls = format_pred(row.get('momentum_score_1day', np.nan))
            pred_1m_str, pred_1m_cls = format_pred(row.get('momentum_score_1month', np.nan))
            pred_3m_str, pred_3m_cls = format_pred(row.get('momentum_score_3month', np.nan))
            pred_6m_str, pred_6m_cls = format_pred(row.get('momentum_score_6month', np.nan))
            
            html_content += f"""
                            <tr>
                                <td>{i+1}</td>
                                <td>{row['code']}</td>
                                <td class="score-cell">{score}</td>
                                <td>{eps}</td>
                                <td>{rev}</td>
                                <td>{per}</td>
                                <td>{pbr}</td>
                                <td>{roe}</td>
                                <td class="{pred_1d_cls}">{pred_1d_str}</td>
                                <td class="{pred_1m_cls}">{pred_1m_str}</td>
                                <td class="{pred_3m_cls}">{pred_3m_str}</td>
                                <td class="{pred_6m_cls}">{pred_6m_str}</td>
                                <td><a href="{minkabu_url}" target="_blank" class="link-btn">みんかぶ</a></td>
                            </tr>
            """
            
        html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """

        
        output_path = os.path.join(self.output_dir, "report.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"HTMLレポートを保存しました: {output_path}")
