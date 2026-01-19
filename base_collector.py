import logging
import os
from datetime import datetime
from finmind_client import get_finmind_api
from database_setup import DatabaseManager

logger = logging.getLogger(__name__)

class BaseStockListCollector:
    """
    一個基礎類別，封裝了按股票列表遍歷數據的通用收集器邏輯。
    子類別需要實現 _call_api 和 _save_data 方法。
    """
    def __init__(self, collector_name):
        self.collector_name = collector_name
        self.api = get_finmind_api()
        self.db_manager = DatabaseManager()

    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """
        由子類別實現，定義如何呼叫 spezifische FinMind API。
        必須返回一個 pandas DataFrame。
        """
        raise NotImplementedError("子類別必須實現 _call_api 方法")

    def _save_data(self, df, stock_id) -> bool:
        """
        由子類別實現，定義如何儲存 spezifische 資料。
        必須返回一個布林值表示成功或失敗。
        """
        raise NotImplementedError("子類別必須實現 _save_data 方法")
        
    def _get_start_date(self, use_custom_range: bool, start_date: str = None) -> str:
        """從設定檔獲取開始日期"""
        if use_custom_range:
            return os.getenv('DEFAULT_START_DATE', '2020-01-01')
        
        env_key = f"{self.collector_name.upper()}_START_DATE"
        return os.getenv(env_key, os.getenv('DEFAULT_START_DATE', '2020-01-01'))

    def run(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """通用的執行邏輯，包含了所有重複的步驟"""
        print(f"--- 正在收集 {self.collector_name} 數據 ---")

        # 1. 決定時間範圍
        effective_start_date = self._get_start_date(use_custom_range, start_date)
        effective_end_date = os.getenv('DEFAULT_END_DATE', datetime.now().strftime('%Y-%m-%d')) if use_custom_range else datetime.now().strftime('%Y-%m-%d')
        
        # 2. 獲取股票列表
        if not stock_list:
            # 使用動態導入避免循環導入
            from taiwan_stock_info import TaiwanStockInfoCollector
            info_collector = TaiwanStockInfoCollector()
            stock_list = info_collector.get_stock_list()
            if not stock_list:
                logger.error("無法獲取股票列表")
                return False, "無法獲取股票列表"

        # 3. 處理斷點續傳
        resume_from_index = 0
        original_total = len(stock_list)
        if progress_manager and not use_custom_range:
            resume_info = progress_manager.get_resume_info(self.collector_name, stock_list)
            if resume_info.get('should_resume'):
                resume_from_index = resume_info.get('resume_from_index', 0)
                stock_list = resume_info.get('remaining_stocks', stock_list)
                print(f"🔄 斷點續傳：從第 {resume_from_index + 1} 支股票開始，剩餘 {len(stock_list)} 支。")
            elif resume_info.get('all_completed', False):
                print(f"✅ 收集器 {self.collector_name} 先前已完成，跳過執行。")
                return True, "已完成"
        
        if not stock_list:
             print(f"✅ 所有股票已處理完成。")
             return True, "已完成"

        # 4. 主迴圈
        success_count = 0
        error_count = 0
        
        for i, stock_id in enumerate(stock_list, 1):
            global_index = resume_from_index + i
            
            # 5. API 速率限制檢查
            if rate_limiter and not rate_limiter.can_call():
                logger.warning("API 調用次數已達上限，執行中斷。")
                break

            print(f"進度: {global_index}/{original_total} | 處理股票: {stock_id}")

            try:
                # 6. API 呼叫
                if rate_limiter:
                    rate_limiter.record_call()
                
                df = self._call_api(stock_id=stock_id, start_date=effective_start_date, end_date=effective_end_date)
                
                # 7. 儲存資料
                if df.empty:
                    logger.info(f"股票 {stock_id} 在指定範圍內無數據。")
                elif self._save_data(df, stock_id):
                    success_count += 1
                else:
                    error_count += 1
                
                # 8. 更新進度
                if progress_manager and not use_custom_range:
                    progress_manager.update_progress(self.collector_name, False, stock_id, global_index)

            except Exception as e:
                error_count += 1
                logger.error(f"處理股票 {stock_id} 時發生未預期錯誤: {e}")
                error_str = str(e)
                if ("Requests reach the upper limit" in error_str) or ("status:402" in error_str) or ("402" in error_str):
                    logger.error("偵測到 FinMind API 上限錯誤 (402)，收集器立即停止！")
                    # 不更新進度，直接 break
                    break
                if progress_manager and not use_custom_range:
                    progress_manager.update_progress(self.collector_name, False, stock_id, global_index, error_occurred=True)
                if error_count > 10:
                    logger.error("錯誤次數過多，停止此收集器。")
                    break

        # 9. 標記完成
        if progress_manager and not use_custom_range and (resume_from_index + i) >= original_total:
             progress_manager.mark_completed(self.collector_name)

        print(f"--- {self.collector_name} 收集完成！成功儲存 {success_count} 支股票的數據，失敗 {error_count} 支。---")
        return True, f"成功處理 {success_count} 支股票"

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None, **kwargs):
        """主要執行方法，供 main.py 調用"""
        return self.run(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            rate_limiter=rate_limiter,
            use_custom_range=use_custom_range,
            progress_manager=progress_manager
        )


class BaseDateListCollector:
    """
    一個基礎類別，封裝了按日期列表遍歷數據的通用收集器邏輯。
    子類別需要實現 _call_api 和 _save_data 方法。
    """
    def __init__(self, collector_name):
        self.collector_name = collector_name
        self.api = get_finmind_api()
        self.db_manager = DatabaseManager()

    def _call_api(self, date: str):
        """由子類別實現，定義如何呼叫 spezifische FinMind API。"""
        raise NotImplementedError("子類別必須實現 _call_api 方法")

    def _save_data(self, df, date: str) -> bool:
        """由子類別實現，定義如何儲存 spezifische 資料。"""
        raise NotImplementedError("子類別必須實現 _save_data 方法")

    def _get_trading_dates(self, start_date, end_date):
        """從資料庫獲取交易日列表的輔助函數"""
        from taiwan_stock_trading_date import TaiwanStockTradingDateCollector
        trading_date_collector = TaiwanStockTradingDateCollector()
        return trading_date_collector.get_trading_dates_list(start_date, end_date)

    def run(self, start_date=None, end_date=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """通用的日期遍歷執行邏輯"""
        print(f"--- 正在收集 {self.collector_name} 數據 ---")
        
        # 決定時間範圍
        if use_custom_range:
            effective_start_date = os.getenv('DEFAULT_START_DATE', '2020-01-01')
            effective_end_date = os.getenv('DEFAULT_END_DATE', datetime.now().strftime('%Y-%m-%d'))
        else:
            # 根據收集器名稱映射到正確的環境變數名稱
            env_mapping = {
                'taiwan_stock_statistics_of_order_book_and_trade': 'TAIWAN_STOCK_ORDER_BOOK_TRADE_START_DATE'
            }
            env_key = env_mapping.get(self.collector_name, f"{self.collector_name.upper()}_START_DATE")
            env_start_date = os.getenv(env_key)
            
            # 如果環境變數值是 'all_time'，轉換為 '1990-01-01'
            if env_start_date == 'all_time':
                effective_start_date = '1990-01-01'
            else:
                effective_start_date = env_start_date or os.getenv('DEFAULT_START_DATE', '2020-01-01')
            
            effective_end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 獲取交易日列表
        date_list = self._get_trading_dates(effective_start_date, effective_end_date)
        if not date_list:
            logger.error("無法獲取交易日列表，收集器無法執行。")
            return False, "無法獲取交易日"

        # 處理斷點續傳
        resume_from_index = 0
        original_total = len(date_list)
        if progress_manager and not use_custom_range:
            resume_info = progress_manager.get_resume_info(self.collector_name, date_list)
            if resume_info.get('should_resume'):
                resume_from_index = resume_info.get('resume_from_index', 0)
                date_list = resume_info.get('remaining_stocks', date_list) # progress_manager 使用 'remaining_stocks'
                print(f"🔄 斷點續傳：從第 {resume_from_index + 1} 個日期開始，剩餘 {len(date_list)} 天。")
            elif resume_info.get('all_completed', False):
                print(f"✅ 收集器 {self.collector_name} 先前已完成，跳過執行。")
                return True, "已完成"
        
        # 主迴圈
        for i, current_date in enumerate(date_list, 1):
            global_index = resume_from_index + i
            if rate_limiter and not rate_limiter.can_call():
                logger.warning("API 調用次數已達上限，執行中斷。")
                break
            
            print(f"進度: {global_index}/{original_total} | 處理日期: {current_date}")
            try:
                if rate_limiter: rate_limiter.record_call()
                df = self._call_api(date=current_date)
                if df.empty:
                    logger.info(f"日期 {current_date} 無數據。")
                else:
                    self._save_data(df, current_date)
                
                if progress_manager: progress_manager.update_progress(self.collector_name, False, current_date, global_index)
            except Exception as e:
                logger.error(f"處理日期 {current_date} 失敗: {e}")
                if progress_manager: progress_manager.update_progress(self.collector_name, False, current_date, global_index, error_occurred=True)

        print(f"--- {self.collector_name} 數據收集完成！---")
        return True, "完成"

    def main(self, start_date=None, end_date=None, rate_limiter=None, use_custom_range=False, progress_manager=None, **kwargs):
        """主要執行方法，供 main.py 調用"""
        return self.run(
            start_date=start_date,
            end_date=end_date,
            rate_limiter=rate_limiter,
            use_custom_range=use_custom_range,
            progress_manager=progress_manager
        )


class BaseOneShotCollector:
    """
    處理一次性 API 呼叫的基礎類別（無參數）。
    """
    def __init__(self, collector_name):
        self.collector_name = collector_name
        self.api = get_finmind_api()
        self.db_manager = DatabaseManager()

    def _call_api(self):
        raise NotImplementedError("子類別必須實現 _call_api 方法")

    def _save_data(self, df) -> bool:
        raise NotImplementedError("子類別必須實現 _save_data 方法")

    def main(self, rate_limiter=None, progress_manager=None, **kwargs):
        print(f"--- 正在收集 {self.collector_name} 數據 ---")
        if rate_limiter and not rate_limiter.can_call():
            logger.warning("API 調用次數已達上限，跳過此收集器。")
            return False, "API Rate Limit"
        
        try:
            df = self._call_api()
            if rate_limiter: rate_limiter.record_call()

            if df.empty:
                logger.warning(f"未獲取到 {self.collector_name} 數據。")
                return True, "No data"
            
            if self._save_data(df):
                print(f"--- {self.collector_name} 數據收集完成！---")
                if progress_manager: progress_manager.mark_completed(self.collector_name)
                return True, "Success"
            else:
                return False, "Save failed"
        except Exception as e:
            logger.error(f"收集 {self.collector_name} 時發生錯誤: {e}")
            return False, str(e)

class BaseDateRangeCollector(BaseOneShotCollector):
    """
    處理需要日期範圍的 API 呼叫的基礎類別。
    """
    def main(self, use_custom_range=False, rate_limiter=None, progress_manager=None, **kwargs):
        print(f"--- 正在收集 {self.collector_name} 數據 ---")
        
        # 決定時間範圍
        if use_custom_range:
            start_date = os.getenv('DEFAULT_START_DATE', '2020-01-01')
            end_date = os.getenv('DEFAULT_END_DATE', datetime.now().strftime('%Y-%m-%d'))
        else:
            env_key = f"{self.collector_name.upper()}_START_DATE"
            start_date = os.getenv(env_key, '1990-01-01')
            if start_date == 'all_time': start_date = '1990-01-01'
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if rate_limiter and not rate_limiter.can_call():
            logger.warning("API 調用次數已達上限，跳過此收集器。")
            return False, "API Rate Limit"

        try:
            df = self._call_api(start_date, end_date)
            if rate_limiter: rate_limiter.record_call()
            
            if df.empty:
                logger.warning(f"未獲取到 {self.collector_name} 數據。")
                return True, "No data"

            if self._save_data(df):
                print(f"--- {self.collector_name} 數據收集完成！---")
                if progress_manager: progress_manager.mark_completed(self.collector_name)
                return True, "Success"
            else:
                return False, "Save failed"
        except Exception as e:
            logger.error(f"收集 {self.collector_name} 時發生錯誤: {e}")
            return False, str(e)
