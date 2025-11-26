import os
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
from . import config

class TopixManager:
    def __init__(self):
        self.tickers_file = config.TICKERS_FILE
        self.jpx_url = config.JPX_URL
        self.base_url = config.JPX_BASE_URL

    def load_tickers(self):
        """
        銘柄リストを読み込む。
        ファイルが存在しない、または古い場合は更新を試みる。
        """
        if self._should_update():
            print("銘柄リストの更新が必要です。JPXから最新データを取得します...")
            try:
                self.update_tickers()
            except Exception as e:
                print(f"銘柄リストの更新に失敗しました: {e}")
                if os.path.exists(self.tickers_file):
                    print("既存のリストを使用します。")
                else:
                    raise RuntimeError("銘柄リストがなく、更新も失敗しました。") from e

        return pd.read_csv(self.tickers_file)["ticker"].tolist()

    def _should_update(self):
        """
        更新が必要かどうかを判定する
        """
        if not os.path.exists(self.tickers_file):
            return True
        
        # ファイルの更新日時を確認
        mtime = datetime.fromtimestamp(os.path.getmtime(self.tickers_file))
        if datetime.now() - mtime > timedelta(days=config.TICKER_UPDATE_INTERVAL_DAYS):
            return True
            
        return False

    def update_tickers(self):
        """
        JPXから最新のExcelをダウンロードしてTOPIX 100銘柄を抽出・保存する
        """
        # 1. JPXのページからExcelのリンクを取得
        excel_url = self._get_excel_url()
        print(f"Excelファイルをダウンロード中: {excel_url}")
        
        # 2. ExcelをダウンロードしてDataFrame化
        # xlrdが必要になる可能性があります
        try:
            df = pd.read_excel(excel_url)
        except ImportError:
             # xlrdがない場合のフォールバック（ユーザーへのメッセージなど）
             # ここではそのままエラーを投げて依存関係の不足を知らせる
             raise ImportError("Excelファイルの読み込みに失敗しました。'xlrd' または 'openpyxl' がインストールされているか確認してください。")

        # 3. TOPIX 100銘柄を抽出
        topix100_tickers = self._extract_topix100(df)
        
        if not topix100_tickers:
            raise ValueError("TOPIX 100銘柄の抽出に失敗しました。Excelのフォーマットが変わった可能性があります。")

        # 4. CSVに保存
        os.makedirs(os.path.dirname(self.tickers_file), exist_ok=True)
        pd.DataFrame({"ticker": topix100_tickers}).to_csv(self.tickers_file, index=False)
        print(f"銘柄リストを更新しました: {len(topix100_tickers)}銘柄")

    def _get_excel_url(self):
        """
        JPXのページをスクレイピングしてExcelのURLを特定する
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(self.jpx_url, headers=headers)
        response.raise_for_status()
        # encodingを明示的に設定（文字化け対策）
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # デバッグ用: ページタイトル表示
        print(f"Page Title: {soup.title.string if soup.title else 'No Title'}")
        
        # "東証上場銘柄一覧" を含むリンクを探す
        # 拡張子が .xls または .xlsx
        candidates = []
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            text = a.get_text(strip=True)
            
            if "xls" in href or "xlsx" in href:
                candidates.append((text, href))
                # print(f"Found Excel link: {text} -> {href}") # Debug
                
                if "東証上場銘柄一覧" in text:
                    return urljoin(self.base_url, href)
        
        # 見つからなかった場合、候補を表示
        print("Candidates found:")
        for t, h in candidates:
            print(f" - {t}: {h}")
            
        # もし "東証上場銘柄一覧" という正確なテキストが見つからなくても、
        # "data_j.xls" というファイル名が含まれていればそれを採用する（フォールバック）
        for t, h in candidates:
            if "data_j.xls" in h:
                print(f"Fallback: Found 'data_j.xls' in {h}")
                return urljoin(self.base_url, h)
        
        raise ValueError("Excelファイルのリンクが見つかりませんでした。")

    def _extract_topix100(self, df):
        """
        DataFrameからTOPIX 100銘柄（Core30 + Large70）を抽出する
        """
        # カラム名の特定（行によってヘッダーがずれている場合があるため調整）
        # 通常、JPXのExcelは数行のヘッダーがある。
        # "コード" や "規模区分" が含まれる行を探す
        
        header_row = -1
        for i in range(10): # 最初の10行を確認
            row_values = df.iloc[i].astype(str).values
            if "コード" in row_values and "規模区分" in row_values:
                header_row = i
                break
        
        if header_row == -1:
            # ヘッダーが見つからない場合、カラム名で直接探してみる（すでにヘッダーとして読み込まれている場合）
            if "コード" in df.columns and "規模区分" in df.columns:
                target_df = df
            else:
                raise ValueError("Excelファイル内に必要なカラム（コード, 規模区分）が見つかりません。")
        else:
            # ヘッダー行を指定して再読み込みしたいが、すでにdfがあるので加工する
            df.columns = df.iloc[header_row]
            target_df = df.iloc[header_row+1:].copy()

        # カラム名の空白除去など
        target_df.columns = [str(c).strip() for c in target_df.columns]
        
        # 抽出ロジック: 規模区分が "TOPIX Core30" または "TOPIX Large70"
        # 注: 実際の値は "TOPIX Core30" など。表記ゆれに注意。
        
        # 必要なカラム
        code_col = "コード"
        size_col = "規模区分"
        
        if code_col not in target_df.columns or size_col not in target_df.columns:
             raise ValueError(f"カラムが見つかりません: {target_df.columns}")

        # フィルタリング
        # 規模区分に "Core30" または "Large70" が含まれるものを抽出
        mask = target_df[size_col].astype(str).apply(lambda x: "Core30" in x or "Large70" in x)
        filtered = target_df[mask]
        
        tickers = []
        for code in filtered[code_col]:
            # コードは通常4桁の数字だが、文字列として扱う
            # 末尾に .T をつける
            try:
                code_str = str(int(code)) # 9432.0 -> 9432
                tickers.append(f"{code_str}.T")
            except:
                continue
                
        return tickers

if __name__ == "__main__":
    # テスト実行
    manager = TopixManager()
    try:
        tickers = manager.load_tickers()
        print(f"取得された銘柄数: {len(tickers)}")
        print(tickers[:5])
    except Exception as e:
        print(e)
