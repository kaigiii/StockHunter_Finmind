
"""
API Rate Limiter Service
Manages API call frequency to avoid hitting rate limits.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

import threading
import core.config as config

class APIRateLimiter:
    """API 調用限制器 (Thread-Safe & Scalable)"""
    def __init__(self, max_calls_per_hour=None):
        base_limit = max_calls_per_hour or int(os.getenv('API_MAX_CALLS_PER_HOUR', 300))
        # 根據 Token 數量擴展上限
        token_count = len(config.FINMIND_API_TOKENS)
        self.max_calls_per_hour = base_limit * (token_count if token_count > 0 else 1)
        
        if token_count > 1:
            logger.info(f"[Revolver Mode]: API 上限已擴展為 {self.max_calls_per_hour}/hr ({token_count} tokens)")
        
        self.call_history = []
        self._lock = threading.Lock()
        
    def can_call(self):
        """檢查是否可以進行 API 調用"""
        with self._lock:
            now = datetime.now()
            # 清除時間窗口外的記錄
            self.call_history = [call_time for call_time in self.call_history 
                               if (now - call_time).total_seconds() < int(os.getenv('API_TIME_WINDOW_SECONDS', 3600))]
            return len(self.call_history) < self.max_calls_per_hour
    
    def record_call(self, count=1):
        """記錄 API 調用"""
        with self._lock:
            for _ in range(count):
                self.call_history.append(datetime.now())
    
    def get_remaining_calls(self):
        """獲取剩餘調用次數"""
        with self._lock:
            now = datetime.now()
            self.call_history = [call_time for call_time in self.call_history 
                               if (now - call_time).total_seconds() < int(os.getenv('API_TIME_WINDOW_SECONDS', 3600))]
            return self.max_calls_per_hour - len(self.call_history)
    
    def get_next_available_time(self):
        """獲取下次可以調用的時間"""
        with self._lock:
            if len(self.call_history) < self.max_calls_per_hour:
                return datetime.now()
            oldest_call = min(self.call_history)
            return oldest_call + timedelta(seconds=int(os.getenv('API_TIME_WINDOW_SECONDS', 3600)))
    
    def detect_api_limit_error(self, error_message):
        """檢測是否是 API 限制錯誤"""
        error_str = str(error_message).lower()
        
        # 檢查 402 狀態碼
        if '"status":402' in error_str or '"status": 402' in error_str:
            return True
        
        # 檢查錯誤訊息關鍵字
        api_limit_keywords = [kw.strip() for kw in os.getenv('API_LIMIT_KEYWORDS', 'upper limit,reach.*limit,402').split(',')]
        for keyword in api_limit_keywords:
            if keyword.lower() in error_str:
                return True
                
        return False
    
    def handle_api_limit_error(self, current_collector_name):
        """
        處理 API 限制錯誤 (Legacy/Fallback)
        注意：主要重試邏輯已移至 services/api.py 的 FinMindRevolver 中。
        此方法僅作紀錄或簡單等待。
        """
        logger.warning(f"[RateLimiter] 收到 API 限制通知 ({current_collector_name})")
        
        # 簡單等待一段時間，避免瘋狂迴圈
        import time
        logger.info("暫停 60 秒...")
        time.sleep(60)
        
        # 總是返回 '1' (繼續)，因為現在由 api.py 負責換 token
        return '1'
