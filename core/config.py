import os
import logging
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# --- 基礎運行環境 ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('StockHunter')

# --- 數據庫配置 ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_USER = os.getenv('DB_USER', 'stockhunter')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'stockhunter123')
DB_NAME = os.getenv('DB_NAME', 'stockhunter')

# --- API 核心配置 ---
FINMIND_API_TOKENS = []
for key, value in os.environ.items():
    if key.startswith('FINMIND_API_TOKEN_') and value.strip():
        token = value.strip()
        if token not in FINMIND_API_TOKENS:
            FINMIND_API_TOKENS.append(token)

if not FINMIND_API_TOKENS:
    single_token = os.getenv('FINMIND_API_TOKEN')
    if single_token and single_token != 'your_api_token':
        FINMIND_API_TOKENS = [single_token]

# --- 頻率限制與節流 ---
API_MAX_CALLS_PER_HOUR = int(os.getenv('API_MAX_CALLS_PER_HOUR', 300))
API_TIME_WINDOW = int(os.getenv('API_TIME_WINDOW_SECONDS', 3600))

# --- API 頻率與重試設定
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 5))
API_MAX_CALLS_PER_HOUR = int(os.getenv('API_MAX_CALLS_PER_HOUR', 300))
API_WAIT_TIME_402 = int(os.getenv('API_WAIT_TIME_402', 600))  # 遇到 402 限制時等待秒數
API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', 5))        # 一般錯誤重試等待秒數
HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', 30))             # API 請求超時時間 (秒)

# 資料庫連線池設定
DB_POOL_MIN = int(os.getenv('DB_POOL_MIN', 1))
DB_POOL_MAX = int(os.getenv('DB_POOL_MAX', 20))

# Web 伺服器設定
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.getenv('WEB_PORT', 8000))

# --- 目錄與路徑 ---
EXPORT_DIR = os.getenv('EXPORT_DIR', 'csv_exports')

# --- 默認數據日期 ---
DEFAULT_START_DATE = os.getenv('DEFAULT_START_DATE', '2020-01-01')

def get_env_variable(key, default=None):
    """獲取環境變數的輔助函數"""
    return os.getenv(key, default)
