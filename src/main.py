import sys
import os
from datetime import datetime, timedelta
from . import config
from .data_manager import TopixManager
from .analyzer import StockAnalyzer
from .visualizer import Visualizer

def main():
    print("=== TOPIX 100 Analysis Started ===")
    
    # 1. 銘柄リストの準備
    print("\n[1/4] Initializing Ticker List...")
    manager = TopixManager()
    try:
        tickers = manager.load_tickers()
        print(f"Loaded {len(tickers)} tickers.")
    except Exception as e:
        print(f"Critical Error loading tickers: {e}")
        sys.exit(1)

    # 2. ファンダメンタルズ分析
    print("\n[2/4] Analyzing Fundamentals...")
    analyzer = StockAnalyzer()
    df_fundamentals = analyzer.get_fundamentals_parallel(tickers)
    
    if df_fundamentals.empty:
        print("No fundamental data retrieved. Exiting.")
        sys.exit(1)
        
    df_scores = analyzer.calculate_scores(df_fundamentals)
    print(f"Scored {len(df_scores)} stocks.")
    
    # 上位銘柄の表示
    print("\nTop 5 Stocks by Score:")
    print(df_scores[["ticker", "score_total", "eps_growth", "roe", "per"]].head(5))

    # 3. 株価データ取得とリターン計算（上位20銘柄）
    print("\n[3/4] Analyzing Price Returns for Top 20 Stocks...")
    top_20_tickers = df_scores["ticker"].head(20).tolist()
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
    
    df_price = analyzer.get_stock_data_bulk(top_20_tickers, start_date, end_date)
    
    if not df_price.empty:
        latest_date = df_price.index.max()
        print(f"Latest data date: {latest_date}")
        df_returns = analyzer.calculate_returns(df_price, latest_date)
    else:
        print("Failed to retrieve price data.")
        df_returns = pd.DataFrame()

    # 4. 可視化とレポート作成
    print("\n[4/4] Generating Visualizations and Report...")
    visualizer = Visualizer()
    visualizer.plot_scores(df_scores, top_n=20)
    visualizer.generate_html_report(df_scores, df_returns, top_n=20)
    
    print(f"\nAnalysis Complete! Check the output directory: {config.OUTPUT_DIR}")
    print(f"Report: {os.path.join(config.OUTPUT_DIR, 'report.html')}")

if __name__ == "__main__":
    main()
