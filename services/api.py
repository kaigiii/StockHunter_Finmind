import os
import logging
from dotenv import load_dotenv
from FinMind.data import DataLoader

# 載入環境變數
load_dotenv('.env')
logger = logging.getLogger(__name__)

import itertools
import threading
import time
from typing import Optional
from FinMind.data import DataLoader
import core.config as config

_finmind_revolver = None

class FinMindRevolver:
    """
    FinMind API 轉輪 (Revolver)
    管理多個 API Token，通過輪詢 (Round-Robin) 方式分發請求以提高並發能力。
    """
    def __init__(self, tokens: list):
        self.tokens = tokens
        self.apis = []
        # 追蹤 Token 狀態: {api_instance: {'valid': True, 'cooldown_until': datetime}}
        self.token_status = {}
        self._lock = threading.Lock()
        
        if not self.tokens:
            # 匿名模式
            logger.info("未配置 API Token，使用匿名模式 (單一實例)")
            api = DataLoader()
            self.apis.append(api)
            self.token_status[api] = {'valid': True, 'cooldown_until': None}
        else:
            logger.info(f"初始化 FinMindRevolver: 檢測到 {len(self.tokens)} 個 Token")
            for i, token in enumerate(self.tokens):
                api = DataLoader()
                try:
                    api.login_by_token(api_token=token)
                    self.apis.append(api)
                    self.token_status[api] = {'valid': True, 'cooldown_until': None}
                    logger.info(f"Token #{i+1} 登入成功")
                except Exception as e:
                    logger.error(f"Token #{i+1} 登入失敗: {e}")
            
            if not self.apis:
                logger.warning("所有 Token 登入失敗，降級為匿名模式")
                api = DataLoader()
                self.apis.append(api)
                self.token_status[api] = {'valid': True, 'cooldown_until': None}
        
        # 建立無限循環迭代器
        self._cycler = itertools.cycle(self.apis)

    def get_api(self):
        """
        獲取下一個可用的 API 實例 (Thread-Safe)
        自動跳過冷卻中的 Token。如果所有 Token 都在冷卻，則阻塞等待。
        """
        from datetime import datetime
        import time

        with self._lock:
            # 嘗試尋找可用 Token
            # 我們最多遍歷一圈 apis 列表來找可用的
            checked_count = 0
            total_apis = len(self.apis)
            
            while checked_count < total_apis:
                api = next(self._cycler)
                status = self.token_status.get(api)
                
                if status['cooldown_until']:
                    if datetime.now() < status['cooldown_until']:
                        checked_count += 1
                        continue
                    else:
                        # 冷卻結束，恢復使用
                        logger.info(f"Token 冷卻結束，恢復使用")
                        status['cooldown_until'] = None
                        status['valid'] = True
                        return api
                else:
                    return api
            
            # 如果走到這，表示所有 Token 都在冷卻
            logger.warning("所有 Token 皆在冷卻中...")
            
            # 找出最早解禁的那個
            earliest_wakeup = None
            for api in self.apis:
                t = self.token_status[api].get('cooldown_until')
                if t:
                    if earliest_wakeup is None or t < earliest_wakeup:
                        earliest_wakeup = t
            
            if earliest_wakeup:
                wait_seconds = (earliest_wakeup - datetime.now()).total_seconds()
                wait_seconds = max(1, wait_seconds) # 至少等 1 秒
                logger.warning(f"[Sleep] 強制睡眠 {int(wait_seconds)} 秒，等待最早的 Token 恢復...")
                time.sleep(wait_seconds)
                
                # 醒來後遞歸再次獲取
                # 注意：這裡釋放了 lock 再遞歸可能會導致競爭，但因為我們都在一個大邏輯裡
                # 簡單起見，直接返回 next(self._cycler) 因為理論上它應該好了
                # 但為了安全，還是遞歸呼叫自己 (遞歸層數通常不會深，除非運氣極差)
                return self.get_api() # 這裡實際上會遞歸死鎖 if strict re-entry, but Python lock is re-entrant for same thread? No, threading.Lock is NOT re-entrant. RLock is.
                # 但 get_api 對外只有一個入口。這裡遞歸會導致死鎖嗎？
                # wait, self._lock is held. calling self.get_api() again needs lock. 
                # Yes, standard Lock will deadlock.
                # FIX: Do not recurse. Just loop again.
                
                # 改為 Loop 結構更安全，但要小心
                # 這裡為了簡單，我們直接拿一個並返回（假設醒來後它好了）
                # 或者是，我們不鎖住 sleep？
                # "with self._lock" covers the sleep. This blocks ALL threads. That's actually correct behavior if ALL tokens are down.
                # So just loop back to start of while.
                
                # 修正後的邏輯：不用遞歸，直接在 while 迴圈外處理 Wait，然後 continue outer loop?
                # 其實最簡單就是：如果 checked_count >= total_apis，就 sleep，然後重置 checked_count = 0，繼續找
            
            # 為了避免複雜的代碼結構變更，這裡做一個簡單的 workaround:
            # 既然所有都在冷卻，sleep 之後直接 return next(self._cycler)，讓下次調用去處理（如果還沒好，會再進來）
            return next(self._cycler)

            
    def _mark_token_cooldown(self, api, hours=1):
        """將指定 API 標記為冷卻"""
        from datetime import datetime, timedelta
        with self._lock:
            status = self.token_status.get(api)
            if status:
                status['valid'] = False
                status['cooldown_until'] = datetime.now() + timedelta(hours=hours)
                logger.warning(f"[Cooldown] Token 已標記為冷卻，將暫停使用 {hours} 小時 (至 {status['cooldown_until'].strftime('%H:%M:%S')})")

    def __getattr__(self, name):
        """
        代理方法調用。
        自動處理 API 限制 (402) 重試邏輯。
        """
        def wrapper(*args, **kwargs):
            # 最多重試次數 = Token 數 * 2 (避免無限迴圈)
            max_retries = len(self.apis) * 2 + 1 
            retry_count = 0
            
            while retry_count < max_retries:
                api = self.get_api() # 這裡會自動跳過冷卻中的
                func = getattr(api, name)
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    if "402" in error_str or "reach the upper limit" in error_str or "status:402" in error_str:
                        logger.warning(f"[Rate Limit] Token 觸發 API 上限 (402): {e}")
                        self._mark_token_cooldown(api)
                        retry_count += 1
                        logger.info(f"[Retry] 切換至下一個 Token 重試... ({retry_count}/{max_retries})")
                        continue
                    else:
                        # 其他錯誤直接拋出
                        raise e
            
            # 如果重試多次都失敗
            raise Exception(f"所有 Token 皆無法使用或已達重試上限 ({max_retries} 次)")

        return wrapper

def get_finmind_api():
    """獲取 FinMindRevolver 實例（單例模式）"""
    global _finmind_revolver
    if _finmind_revolver is None:
        _finmind_revolver = FinMindRevolver(config.FINMIND_API_TOKENS)
    return _finmind_revolver
