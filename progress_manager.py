"""
進度管理器 - 支持斷點續傳功能
每個收集器獨立記錄進度，支持按股票代號或時間續傳
包含 API 調用限制管理功能
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class CollectorProgressManager:
    """收集器進度管理器"""
    
    def __init__(self, progress_file='collector_progress.json'):
        self.progress_file = progress_file
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """載入進度檔案"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"載入進度檔案失敗: {e}")
        
        return {
            "last_updated": None,
            "collectors": {}
        }
    
    def _save_progress(self):
        """保存進度檔案"""
        self.progress["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存進度檔案失敗: {e}")
    
    def get_collector_progress(self, collector_name: str, use_custom_range: bool = False) -> Dict:
        """獲取收集器進度
        
        Args:
            collector_name: 收集器名稱
            use_custom_range: 是否使用自定義時間範圍
            
        Returns:
            收集器進度資訊
        """
        # 自定義範圍不支持斷點續傳
        if use_custom_range:
            return {"supports_resume": False, "reason": "自定義時間範圍不支持斷點續傳"}
        
        collector_key = f"{collector_name}_full_range"
        
        if collector_key not in self.progress["collectors"]:
            return {
                "supports_resume": True,
                "is_new": True,
                "completed": False,
                "progress_type": self._get_progress_type(collector_name),
                "last_position": None
            }
        
        collector_progress = self.progress["collectors"][collector_key]
        return {
            "supports_resume": True,
            "is_new": False,
            "completed": collector_progress.get("completed", False),
            "progress_type": collector_progress.get("progress_type"),
            "last_position": collector_progress.get("last_position"),
            "total_processed": collector_progress.get("total_processed", 0),
            "last_updated": collector_progress.get("last_updated"),
            "error_count": collector_progress.get("error_count", 0)
        }
    
    def _get_progress_type(self, collector_name: str) -> str:
        """判斷收集器的進度追蹤類型
        
        基於股票代號的收集器：記錄最後處理的股票代號
        基於時間的收集器：記錄最後處理的日期
        """
        # 基於時間的收集器（這些通常按日期範圍收集）
        time_based_collectors = [
            'taiwan_stock_trading_date',
            'taiwan_stock_total_return_index',
            'taiwan_stock_total_margin_purchase_short_sale',
            'taiwan_stock_total_institutional_investors',
            'taiwan_daily_short_sale_balances',
            'taiwan_various_indicators5_seconds'
        ]
        
        if collector_name in time_based_collectors:
            return "time_based"
        else:
            return "stock_based"
    
    def update_progress(self, collector_name: str, use_custom_range: bool, 
                       last_position: Union[str, int], total_processed: int = None,
                       completed: bool = False, error_occurred: bool = False):
        """更新收集器進度
        
        Args:
            collector_name: 收集器名稱
            use_custom_range: 是否使用自定義時間範圍
            last_position: 最後處理位置（股票代號或日期）
            total_processed: 已處理總數
            completed: 是否完成
            error_occurred: 是否發生錯誤
        """
        # 自定義範圍不記錄進度
        if use_custom_range:
            return
        
        collector_key = f"{collector_name}_full_range"
        
        if collector_key not in self.progress["collectors"]:
            self.progress["collectors"][collector_key] = {
                "progress_type": self._get_progress_type(collector_name),
                "started_at": datetime.now().isoformat(),
                "total_processed": 0,
                "error_count": 0
            }
        
        collector_progress = self.progress["collectors"][collector_key]
        collector_progress["last_position"] = last_position
        collector_progress["last_updated"] = datetime.now().isoformat()
        collector_progress["completed"] = completed
        
        if total_processed is not None:
            collector_progress["total_processed"] = total_processed
        
        if error_occurred:
            collector_progress["error_count"] = collector_progress.get("error_count", 0) + 1
        
        # 如果完成，記錄完成時間
        if completed:
            collector_progress["completed_at"] = datetime.now().isoformat()
        
        self._save_progress()
    
    def get_resume_info(self, collector_name: str, stock_list: List[str]) -> Dict:
        """獲取續傳資訊
        
        Args:
            collector_name: 收集器名稱
            stock_list: 完整股票列表
            
        Returns:
            續傳資訊
        """
        progress_info = self.get_collector_progress(collector_name, use_custom_range=False)
        
        if not progress_info["supports_resume"] or progress_info["is_new"]:
            return {
                "should_resume": False,
                "remaining_stocks": stock_list,
                "resume_from_index": 0,
                "already_processed": 0
            }
        
        if progress_info["completed"]:
            # 檢查已處理的數量是否匹配當前股票列表
            processed_count = progress_info.get("total_processed", 0)
            current_total = len(stock_list)
            
            # 如果當前股票列表更大，說明是從小列表切換到完整列表
            # 此時應該檢查是否已經完成了當前所有股票
            if processed_count >= current_total:
                return {
                    "should_resume": False,
                    "all_completed": True,
                    "remaining_stocks": [],
                    "resume_from_index": current_total,
                    "already_processed": current_total,
                    "message": "收集器已完成，無需續傳"
                }
            elif processed_count < current_total:
                # 檢查最後處理的股票是否在當前列表中
                last_position = progress_info.get("last_position")
                if last_position and last_position in stock_list:
                    # 從最後位置繼續
                    try:
                        resume_index = stock_list.index(last_position) + 1
                        remaining_stocks = stock_list[resume_index:]
                        return {
                            "should_resume": True,
                            "remaining_stocks": remaining_stocks,
                            "resume_from_index": resume_index,
                            "already_processed": resume_index,
                            "message": f"從最後位置 {last_position} 繼續收集"
                        }
                    except ValueError:
                        pass
                
                # 無法確定位置，重新開始
                return {
                    "should_resume": False,
                    "remaining_stocks": stock_list,
                    "resume_from_index": 0,
                    "already_processed": 0,
                    "message": f"檢測到股票列表變更（之前:{processed_count}，現在:{current_total}），重新開始收集"
                }
        
        last_position = progress_info["last_position"]
        progress_type = progress_info["progress_type"]
        
        if progress_type == "stock_based" and last_position:
            # 找到最後處理的股票位置
            try:
                last_index = stock_list.index(last_position)
                resume_from_index = last_index + 1
                remaining_stocks = stock_list[resume_from_index:]
                
                return {
                    "should_resume": True,
                    "remaining_stocks": remaining_stocks,
                    "resume_from_index": resume_from_index,
                    "already_processed": resume_from_index,
                    "last_processed_stock": last_position,
                    "message": f"從股票 {last_position} 的下一個位置續傳"
                }
            except ValueError:
                # 找不到股票代號，可能股票列表已變更
                return {
                    "should_resume": False,
                    "remaining_stocks": stock_list,
                    "resume_from_index": 0,
                    "already_processed": 0,
                    "message": f"找不到上次處理的股票 {last_position}，從頭開始"
                }
        
        # 時間基礎的收集器續傳邏輯
        if progress_type == "time_based" and last_position:
            try:
                # 對於時間基礎的收集器，stock_list 實際上是日期列表
                last_date_index = stock_list.index(last_position)
                resume_from_index = last_date_index + 1
                remaining_dates = stock_list[resume_from_index:]
                
                return {
                    "should_resume": True,
                    "remaining_stocks": remaining_dates,
                    "resume_from_index": resume_from_index,
                    "already_processed": resume_from_index,
                    "last_processed_date": last_position,
                    "message": f"從日期 {last_position} 的下一個位置續傳"
                }
            except ValueError:
                # 找不到日期，可能日期列表已變更
                return {
                    "should_resume": False,
                    "remaining_stocks": stock_list,
                    "resume_from_index": 0,
                    "already_processed": 0,
                    "message": f"找不到上次處理的日期 {last_position}，從頭開始"
                }
        
        # 對於未知的進度類型，不支持續傳
        return {
            "should_resume": False,
            "remaining_stocks": stock_list,
            "resume_from_index": 0,
            "already_processed": 0,
            "message": "未知的進度類型，暫不支持續傳"
        }
    
    def mark_completed(self, collector_name: str, use_custom_range: bool = False):
        """標記收集器完成"""
        # 獲取當前進度，保持現有的 last_position
        collector_key = f"{collector_name}_full_range"
        if collector_key in self.progress["collectors"]:
            current_progress = self.progress["collectors"][collector_key]
            current_last_position = current_progress.get("last_position")
            current_total_processed = current_progress.get("total_processed", 0)
            
            # 更新完成狀態，但保持現有的位置信息
            self.update_progress(
                collector_name, 
                use_custom_range, 
                current_last_position, 
                current_total_processed, 
                completed=True
            )
        else:
            # 如果沒有現有進度，直接標記完成
            self.update_progress(collector_name, use_custom_range, None, completed=True)
    
    def reset_collector(self, collector_name: str):
        """重置單個收集器進度"""
        collector_key = f"{collector_name}_full_range"
        if collector_key in self.progress["collectors"]:
            del self.progress["collectors"][collector_key]
            self._save_progress()
            print(f"✅ 已重置收集器 {collector_name} 的進度")
        else:
            print(f"📝 收集器 {collector_name} 尚無進度記錄")
    
    def reset_all_progress(self):
        """重置所有收集器進度"""
        if self.progress["collectors"]:
            collector_count = len(self.progress["collectors"])
            self.progress["collectors"] = {}
            self._save_progress()
            print(f"✅ 已重置所有 {collector_count} 個收集器的進度")
        else:
            print("📝 目前無任何進度記錄需要重置")
    
    def show_status(self):
        """顯示所有收集器狀態"""
        print("\n" + "="*80)
        print("📊 收集器進度狀態")
        print("="*80)
        
        if not self.progress["collectors"]:
            print("📝 尚無任何收集器進度記錄")
            return
        
        for collector_key, progress in self.progress["collectors"].items():
            collector_name = collector_key.replace("_full_range", "")
            status_icon = "✅" if progress.get("completed", False) else "⏳"
            progress_type = progress.get("progress_type", "unknown")
            last_position = progress.get("last_position", "無")
            total_processed = progress.get("total_processed", 0)
            error_count = progress.get("error_count", 0)
            
            print(f"\n{status_icon} {collector_name}")
            print(f"   進度類型: {progress_type}")
            print(f"   最後位置: {last_position}")
            print(f"   已處理: {total_processed} 項")
            if error_count > 0:
                print(f"   錯誤次數: {error_count}")
            
            last_updated = progress.get("last_updated")
            if last_updated:
                print(f"   更新時間: {last_updated}")
        
        print("\n" + "="*80)

    def is_collection_completed(self, task_key: str, use_custom_range: bool = False) -> bool:
        """
        檢查特定任務是否已完成
        
        Args:
            task_key: 任務鍵值（可以是收集器名稱或特定任務標識）
            use_custom_range: 是否使用自定義範圍
            
        Returns:
            bool: 如果已完成返回True，否則返回False
        """
        try:
            progress_data = self._load_progress()
            if not progress_data:
                return False
            
            range_key = "custom_range" if use_custom_range else "full_range"
            
            # 檢查是否在已完成列表中
            if range_key in progress_data and "completed" in progress_data[range_key]:
                return task_key in progress_data[range_key]["completed"]
            
            return False
            
        except Exception as e:
            print(f"檢查完成狀態時發生錯誤: {e}")
            return False
    
    def mark_collection_completed(self, task_key: str, use_custom_range: bool = False):
        """
        標記特定任務為已完成
        
        Args:
            task_key: 任務鍵值（可以是收集器名稱或特定任務標識）
            use_custom_range: 是否使用自定義範圍
        """
        try:
            progress_data = self._load_progress()
            if not progress_data:
                progress_data = {}
            
            range_key = "custom_range" if use_custom_range else "full_range"
            
            # 確保結構存在
            if range_key not in progress_data:
                progress_data[range_key] = {}
            if "completed" not in progress_data[range_key]:
                progress_data[range_key]["completed"] = []
            
            # 添加到已完成列表
            if task_key not in progress_data[range_key]["completed"]:
                progress_data[range_key]["completed"].append(task_key)
                progress_data[range_key]["last_updated"] = datetime.now().isoformat()
                
                # 更新實例數據並儲存進度
                self.progress_data = progress_data
                self._save_progress()
                print(f"任務 {task_key} 已標記為完成")
            
        except Exception as e:
            print(f"標記完成狀態時發生錯誤: {e}")


class APIRateLimiter:
    """API 調用限制器"""
    def __init__(self, max_calls_per_hour=None):
        self.max_calls_per_hour = max_calls_per_hour or int(os.getenv('API_MAX_CALLS_PER_HOUR', 30))
        self.call_history = []
        
    def can_call(self):
        """檢查是否可以進行 API 調用"""
        now = datetime.now()
        # 清除時間窗口外的記錄
        self.call_history = [call_time for call_time in self.call_history 
                           if (now - call_time).total_seconds() < int(os.getenv('API_TIME_WINDOW_SECONDS', 3600))]
        return len(self.call_history) < self.max_calls_per_hour
    
    def record_call(self, count=1):
        """記錄 API 調用"""
        for _ in range(count):
            self.call_history.append(datetime.now())
    
    def get_remaining_calls(self):
        """獲取剩餘調用次數"""
        now = datetime.now()
        self.call_history = [call_time for call_time in self.call_history 
                           if (now - call_time).total_seconds() < int(os.getenv('API_TIME_WINDOW_SECONDS', 3600))]
        return self.max_calls_per_hour - len(self.call_history)
    
    def get_next_available_time(self):
        """獲取下次可以調用的時間"""
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
        """處理 API 限制錯誤"""
        logger.warning("🚨 檢測到 API 調用上限錯誤 (402)")
        
        # 強制設定已達上限（將調用歷史填滿）
        self.call_history = [datetime.now() for _ in range(self.max_calls_per_hour)]
        
        next_time = self.get_next_available_time()
        wait_seconds = (next_time - datetime.now()).total_seconds()
        
        print(f"\n🚨 API 調用已達上限！")
        print(f"📊 當前收集器: {current_collector_name}")
        print(f"⏰ 需要等待至: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 等待時間: {int(wait_seconds/60)} 分 {int(wait_seconds%60)} 秒")
        
        # 詢問使用者選擇
        print("\n🔧 處理選項:")
        print("1. 等待並繼續執行")
        print("2. 退出程式")
        print("3. 跳過當前收集器並繼續")
        
        while True:
            try:
                choice = input("請選擇 (1/2/3): ").strip()
                if choice in ['1', '2', '3']:
                    return choice
                else:
                    print("❌ 請輸入 1、2 或 3")
            except KeyboardInterrupt:
                print("\n\n👋 已中斷程式")
                return '2'
