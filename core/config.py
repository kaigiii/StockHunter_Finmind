import os
import logging
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# 統一的日誌配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StockHunter')

# 數據庫配置
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_USER = os.getenv('DB_USER', 'stockhunter')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'stockhunter123')
DB_NAME = os.getenv('DB_NAME', 'stockhunter')

# API 配置
# 多 Token 支持
FINMIND_API_TOKENS = []

# 支援多行定義 (FINMIND_API_TOKEN_1, FINMIND_API_TOKEN_2...)
for key, value in os.environ.items():
    if key.startswith('FINMIND_API_TOKEN_') and value.strip():
        token = value.strip()
        if token not in FINMIND_API_TOKENS:
            FINMIND_API_TOKENS.append(token)

# 向後兼容：如果沒有設定 FINMIND_API_TOKENS，嘗試讀取單個 token
if not FINMIND_API_TOKENS:
    single_token = os.getenv('FINMIND_API_TOKEN')
    if single_token and single_token != 'your_api_token':
        FINMIND_API_TOKENS = [single_token]


# 默認日期配置
DEFAULT_START_DATE = os.getenv('DEFAULT_START_DATE', '2020-01-01')

def get_env_variable(key, default=None):
    """獲取環境變數的輔助函數"""
    return os.getenv(key, default)
