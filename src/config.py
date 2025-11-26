import os

# 分析設定
YEARS = 3  # 分析対象期間（年）
RETRY_DELAY = 2  # APIリトライ時の待機時間（秒）
MAX_RETRIES = 3  # APIリトライ回数

# スコアリングの重み
WEIGHTS = {
    "score_eps": 1.0,
    "score_rev": 1.0,
    "score_roe": 1.0,
    "score_per": 1.0,
    "score_pbr": 1.0
}

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "output")
TICKERS_FILE = os.path.join(DATA_DIR, "tickers.csv")

# ディレクトリが存在しない場合は作成
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# JPX関連
JPX_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
JPX_BASE_URL = "https://www.jpx.co.jp"
TICKER_UPDATE_INTERVAL_DAYS = 180  # 銘柄リストの更新間隔（日）
