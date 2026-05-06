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
        # 全局冷卻計時器 (用於同步所有線程)
        self.global_cooldown_until = None
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
            total_apis = len(self.apis)
            
            while True:
                # 1. 檢查是否有全局冷卻 (Global Cooldown)
                # 這表示已經有線程發現全部 Token 都掛了，並設定了鬧鐘
                if self.global_cooldown_until:
                    now = datetime.now()
                    if now < self.global_cooldown_until:
                        # 還有時間，繼續睡 Wait silently
                        wait_seconds = (self.global_cooldown_until - now).total_seconds()
                        if wait_seconds > 0:
                            # 釋放鎖並睡眠 (不印 Log 以免洗版)
                            self._lock.release()
                            try:
                                time.sleep(min(wait_seconds + 0.5, 5)) # 每 5 秒醒來一次檢查，保持靈活性
                            finally:
                                self._lock.acquire()
                            continue
                    else:
                        # 全局時間已到，解除警報，重置狀態
                        self.global_cooldown_until = None
                        # 順便把所有稍微過期的 Token 狀態重置，雖然下面循環也會做，但這樣更明確
                        logger.info("全局冷卻結束，恢復運作")

                # 2. 遍歷尋找可用 Token
                for _ in range(total_apis):
                    api = next(self._cycler)
                    status = self.token_status.get(api)
                    
                    if status['cooldown_until']:
                        if datetime.now() < status['cooldown_until']:
                            continue
                        else:
                            # 冷卻結束，恢復使用
                            logger.info(f"Token 冷卻結束，恢復使用")
                            status['cooldown_until'] = None
                            status['valid'] = True
                            return api
                    else:
                        # 找到可用 Token
                        return api
                
                # 3. 如果跑到這，表示剛剛檢查一輪發現所有 Token 都在冷卻
                # 找出最早解禁的時間，設定全局冷卻
                
                if self.global_cooldown_until:
                     # 可能別的線程剛好設定了，continue 重跑流程 1
                     continue

                earliest_wakeup = None
                for api in self.apis:
                    t = self.token_status[api].get('cooldown_until')
                    if t:
                        if earliest_wakeup is None or t < earliest_wakeup:
                            earliest_wakeup = t
                
                if earliest_wakeup:
                    # 設定全局冷卻時間
                    self.global_cooldown_until = earliest_wakeup
                    wait_seconds = (earliest_wakeup - datetime.now()).total_seconds()
                    
                    if wait_seconds > 0:
                        logger.warning(f"[Sleep] 所有 Token ({len(self.apis)} 個) 冷卻中... 全局暫停 {int(wait_seconds)+1} 秒 (至 {earliest_wakeup.strftime('%H:%M:%S')})")
                    else:
                        # 剛好到期，不用設
                        self.global_cooldown_until = None
                        continue
                        
                else:
                    # 理論上不該發生，防止無窮迴圈
                    time.sleep(1)

    def _mark_token_cooldown(self, api, seconds=None):
        """將指定 API 標記為冷卻"""
        from datetime import datetime, timedelta
        if seconds is None:
            seconds = config.API_WAIT_TIME_402
            
        with self._lock:
            status = self.token_status.get(api)
            if status:
                status['valid'] = False
                status['cooldown_until'] = datetime.now() + timedelta(seconds=seconds)
                logger.warning(f"[Cooldown] Token 已標記為冷卻，將暫停使用 {seconds} 秒 (至 {status['cooldown_until'].strftime('%H:%M:%S')})")

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
                        # 其他錯誤（網路抖動等）
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"[Error] API 請求異常: {e}，將在 {config.API_RETRY_DELAY} 秒後重試...")
                            time.sleep(config.API_RETRY_DELAY)
                            continue
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
