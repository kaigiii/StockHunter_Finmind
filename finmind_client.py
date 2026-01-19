import os
import logging
from dotenv import load_dotenv
from FinMind.data import DataLoader

# 載入環境變數
load_dotenv('config.env')
logger = logging.getLogger(__name__)

_finmind_api = None

def _login_finmind(api):
    """登入 FinMind API"""
    try:
        api_token = os.getenv('FINMIND_API_TOKEN')
        user_id = os.getenv('FINMIND_USER_ID')
        password = os.getenv('FINMIND_PASSWORD')
        
        if api_token and api_token != 'your_api_token':
            api.login_by_token(api_token=api_token)
            logger.info("使用API Token登入成功")
        elif user_id and password and user_id != 'your_user_id' and password != 'your_password':
            api.login(user_id=user_id, password=password)
            logger.info("使用用戶名密碼登入成功")
        else:
            logger.info("未配置FinMind登入資訊，使用匿名模式")
    except Exception as e:
        logger.warning(f"FinMind登入失敗，繼續使用匿名模式: {e}")

def get_finmind_api():
    """獲取 FinMind API 實例（單例模式）"""
    global _finmind_api
    if _finmind_api is None:
        _finmind_api = DataLoader()
        _login_finmind(_finmind_api)
    return _finmind_api
