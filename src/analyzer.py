import time
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from . import config

class StockAnalyzer:
    def __init__(self):
        self.years = config.YEARS
        self.weights = config.WEIGHTS

    def calculate_change_rate(self, series, years=3):
        """
        単純な変化率を計算する関数
        """
        sorted_series = series.dropna().sort_index()
        if len(sorted_series) < years + 1:
            return None
        start = sorted_series.iloc[-(years+1)]
        end = sorted_series.iloc[-1]
        if start == 0:
            return None
        return (end - start) / abs(start)

    def get_fundamental_single(self, ticker):
        """
        1銘柄分のファンダメンタルズを取得
        """
        for attempt in range(config.MAX_RETRIES):
            try:
                stock = yf.Ticker(ticker)
                result = {"ticker": ticker}
                
                # 財務諸表データの取得（キャッシュされる場合があるため、明示的に取得）
                # yfinanceのバージョンによっては income_stmt が空の場合があるためエラーハンドリング
                try:
                    income_stmt = stock.income_stmt
                    if income_stmt is None or income_stmt.empty:
                        # 四半期データなども試すか、あるいは諦める
                        result["has_recent_missing_data"] = True
                        return result
                    df = income_stmt.T
                except Exception:
                    result["has_recent_missing_data"] = True
                    return result

                # 1. 成長率指標
                try:
                    eps_series = df["Diluted EPS"]
                    result["eps_growth"] = self.calculate_change_rate(eps_series, self.years)
                    if eps_series.iloc[:2].isna().any():
                        result["has_recent_missing_data"] = True
                except KeyError:
                    result["eps_growth"] = np.nan
                    result["has_recent_missing_data"] = True

                try:
                    rev_series = df["Total Revenue"]
                    result["revenue_growth"] = self.calculate_change_rate(rev_series, self.years)
                    if rev_series.iloc[:2].isna().any():
                        result["has_recent_missing_data"] = True
                except KeyError:
                    result["revenue_growth"] = np.nan
                    result["has_recent_missing_data"] = True

                # 2. バリュエーション指標
                try:
                    info = stock.info
                    result["per"] = info.get("trailingPE", None)
                    result["pbr"] = info.get("priceToBook", None)
                    result["roe"] = info.get("returnOnEquity", None)
                    
                    if any(pd.isna(x) for x in [result["per"], result["pbr"], result["roe"]]):
                        result["has_recent_missing_data"] = True
                except Exception:
                    result["per"] = result["pbr"] = result["roe"] = None
                    result["has_recent_missing_data"] = True

                if "has_recent_missing_data" not in result:
                    result["has_recent_missing_data"] = False

                return result

            except Exception as e:
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(config.RETRY_DELAY)
                    continue
                else:
                    # print(f"Error processing {ticker}: {str(e)}")
                    return None

    def get_fundamentals_parallel(self, tickers):
        """
        並列処理でファンダメンタルズを取得
        """
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(self.get_fundamental_single, t): t for t in tickers}
            for future in tqdm(as_completed(future_to_ticker), total=len(tickers), desc="ファンダメンタルズ分析中"):
                data = future.result()
                if data is not None:
                    results.append(data)
        
        return pd.DataFrame(results)

    def min_max(self, series, reverse=False):
        s = series.copy()
        if reverse:
            s = s.max() - s
        return (s - s.min()) / (s.max() - s.min() + 1e-9)

    def calculate_scores(self, df):
        """
        スコア計算（ベクトル演算）
        Min-Maxではなくパーセンタイル順位（0.0-1.0）を使用
        """
        # 欠損データの除外
        df = df[~df["has_recent_missing_data"]].reset_index(drop=True)
        
        cols = ["eps_growth", "revenue_growth", "per", "pbr", "roe"]
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df.dropna(subset=cols).reset_index(drop=True)
        
        # スコア計算 (パーセンタイル順位)
        # ascending=True: 大きい方が良い (EPS, Revenue, ROE)
        # ascending=False: 小さい方が良い (PER, PBR)
        
        df["score_eps"] = df["eps_growth"].rank(pct=True, ascending=True)
        df["score_rev"] = df["revenue_growth"].rank(pct=True, ascending=True)
        df["score_roe"] = df["roe"].rank(pct=True, ascending=True)
        
        # PER, PBRは低い方が良いので ascending=False
        df["score_per"] = df["per"].rank(pct=True, ascending=False)
        df["score_pbr"] = df["pbr"].rank(pct=True, ascending=False)
        
        # 総合スコア
        weighted_sum = sum(df[col] * self.weights[col] for col in self.weights)
        total_weight = sum(self.weights.values())
        df["score_total"] = weighted_sum / total_weight
        
        return df.sort_values("score_total", ascending=False).reset_index(drop=True)

    def get_stock_data_bulk(self, tickers, start_date, end_date):
        """
        株価データの一括取得（yfinance.downloadを使用）
        """
        # yfinance.downloadはマルチインデックスを返すため、扱いやすい形に整形する
        try:
            # auto_adjust=FalseでAdj Closeを取得
            data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=False, group_by='ticker', threads=True, progress=True)
            
            # データ構造の変換: Tickerを列ではなく行（インデックス）に持ちたい
            # downloadの結果は (Date, (Ticker, OHLCV...)) ではなく (Date, (OHLCV..., Ticker)) のようなMultiIndex columns
            # 形式: Columns = MultiIndex([(Adj Close, 1332.T), ...])
            
            # スタックして整形
            df_stack = data.stack(level=0).reset_index()
            # カラム名の修正: level_1 が Ticker になっているはず（yfinanceのバージョンによる）
            # 最近のyfinanceは columns = (Price, Ticker) の形
            
            # シンプルにループで取得する方が確実性が高い場合もあるが、高速化のためにdownloadを使う
            # しかし、yfinanceのdownloadは戻り値の形式が複雑でバージョン依存が激しいため、
            # ここでは並列処理で個別に取得する方式を採用する（get_fundamental_singleと同様）
            # 信頼性を優先
            return self.get_stock_data_parallel(tickers, start_date, end_date)
            
        except Exception as e:
            print(f"Bulk download failed, falling back to parallel fetch: {e}")
            return self.get_stock_data_parallel(tickers, start_date, end_date)

    def get_stock_data_single(self, ticker, start_date, end_date):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date, auto_adjust=False)
            if hist.empty:
                return None
            
            hist = hist[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Dividends']]
            hist['SecuritiesCode'] = ticker
            hist['Date'] = hist.index
            hist['ExpectedDividend'] = hist['Dividends'].fillna(0)
            return hist
        except:
            return None

    def get_stock_data_parallel(self, tickers, start_date, end_date):
        data_list = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(self.get_stock_data_single, t, start_date, end_date): t for t in tickers}
            for future in tqdm(as_completed(future_to_ticker), total=len(tickers), desc="株価データ取得中"):
                res = future.result()
                if res is not None:
                    data_list.append(res)
        
        if not data_list:
            return pd.DataFrame()
        return pd.concat(data_list)

    def calculate_returns(self, df_price, latest_date):
        """
        リターンと配当込みリターン（予測値と呼称されていたもの）を計算
        """
        results = []
        tickers = df_price["SecuritiesCode"].unique()
        
        for code in tickers:
            df_t = df_price[df_price["SecuritiesCode"] == code].copy()
            if df_t.empty:
                continue
                
            # 最新日付のデータが存在するか確認
            if latest_date not in df_t.index:
                # 最新日付がない場合は、その銘柄の最新データを使うか、スキップする
                # ここではスキップ
                continue
                
            curr = df_t.loc[latest_date]
            close_col = "Adj Close"
            
            # 過去の価格を取得（営業日ベースで近似）
            # 1ヶ月=21日, 3ヶ月=63日, 6ヶ月=126日
            periods = {
                "1day": 1,
                "1month": 21,
                "3month": 63,
                "6month": 126
            }
            
            res = {"SecuritiesCode": code}
            
            for name, days in periods.items():
                if len(df_t) > days:
                    prev_price = df_t[close_col].iloc[-(days+1)]
                    curr_price = df_t[close_col].iloc[-1]
                    ret = (curr_price - prev_price) / prev_price
                    
                    # 配当（期間中の合計）
                    # iloc[-(days+1):] の範囲の配当を合計
                    div_sum = df_t["ExpectedDividend"].iloc[-(days+1):].sum()
                    # 配当利回り的なものを加算（簡易計算）
                    # 元コードのロジック: return + ExpectedDividend (これは絶対値の加算になっていた？)
                    # 元コード: features["return_1day"] + features["ExpectedDividend"]
                    # ここで ExpectedDividend はその日の配当。
                    # 元コードの意図: 「予測」として、リターン + 配当 を指標にしている。
                    # ここでは元コードのロジックを踏襲しつつ、少し明確にする。
                    # ただし、元コードは `features` (1行) に対して計算していたので、
                    # その日の配当だけを足していた可能性が高い。
                    # 今回は「期間リターン」+「期間中の配当利回り」とするのが自然だが、
                    # ユーザーの意図（元コード）に合わせるなら、
                    # predict = return + dividend_yield ではなく、単にスコアとして足し合わせている。
                    
                    # ここではシンプルに:
                    # リターン = (現在価格 - 過去価格) / 過去価格
                    # 予測スコア = リターン + (期間中の配当合計 / 過去価格)
                    
                    div_yield = div_sum / prev_price if prev_price > 0 else 0
                    res[f"return_{name}"] = ret
                    # 予測ではなくモメンタムスコアとして扱う
                    res[f"momentum_score_{name}"] = ret + div_yield
                else:
                    res[f"return_{name}"] = np.nan
                    res[f"momentum_score_{name}"] = np.nan
            
            results.append(res)
            
        return pd.DataFrame(results)
