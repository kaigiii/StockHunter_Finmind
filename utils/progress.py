
"""
Collector Progress Manager (Database Version)
Tracks the progress of data collectors using PostgreSQL to support robust concurrency.
"""

import logging
from typing import Dict, List
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class CollectorProgressManager:
    """收集器進度管理器 (資料庫版)"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_collector_progress(self, collector_name: str, use_custom_range: bool = False) -> Dict:
        """
        獲取收集器進度統計
        注意：在 DB 版中，我們不再依賴 'last_position'，而是看 completed count
        """
        if use_custom_range:
            return {"supports_resume": False, "reason": "自定義時間範圍不支持斷點續傳"}
        
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*), MAX(updated_at)
                        FROM collector_progress 
                        WHERE collector_name = %s AND status = 'DONE'
                    """, (collector_name,))
                    result = cursor.fetchone()
                    count = result[0] if result else 0
                    last_updated = result[1] if result else None
            
            return {
                "supports_resume": True,
                "is_new": count == 0,
                "completed": False, # DB 模式下很難定義什麼叫"已完成"，除非對比總數
                "total_processed": count,
                "last_updated": last_updated.isoformat() if last_updated else None
            }
        except Exception as e:
            logger.error(f"獲取進度失敗: {e}")
            return {"supports_resume": False, "error": str(e)}

    def update_progress(self, collector_name: str, use_custom_range: bool, 
                       item_id: str, global_index: int = 0, error_occurred: bool = False):
        """
        更新進度：將完成的項目寫入資料庫
        """
        if use_custom_range or error_occurred:
            return
            
        try:
            # 使用 INSERT ON CONFLICT DO NOTHING 避免重複錯誤
            # 這裡我們只記錄成功的項目
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO collector_progress (collector_name, item_id, status)
                        VALUES (%s, %s, 'DONE')
                        ON CONFLICT (collector_name, item_id) 
                        DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                    """, (collector_name, str(item_id)))
                    conn.commit()
        except Exception as e:
            logger.error(f"更新進度失敗 ({collector_name}, {item_id}): {e}")

    def get_resume_info(self, collector_name: str, full_list: List[str]) -> Dict:
        """
        獲取續傳資訊：回傳尚未完成的項目列表
        """
        try:
            # 1. 從資料庫獲取所有已完成的 item_id
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT item_id 
                        FROM collector_progress 
                        WHERE collector_name = %s AND status = 'DONE'
                    """, (collector_name,))
                    rows = cursor.fetchall()
            
            completed_set = {row[0] for row in rows}
            
            # 2. 過濾列表
            # 注意維持原始順序
            remaining_items = [item for item in full_list if str(item) not in completed_set]
            
            total_count = len(full_list)
            completed_count = len(completed_set)
            remaining_count = len(remaining_items)
            
            if remaining_count == 0:
                 return {
                    "should_resume": False,
                    "all_completed": True,
                    "remaining_stocks": [],
                    "resume_from_index": total_count,
                    "already_processed": total_count,
                    "message": "收集器已完成，無需續傳"
                }
            
            if completed_count == 0:
                 return {
                    "should_resume": True,
                    "remaining_stocks": full_list,
                    "resume_from_index": 0,
                    "already_processed": 0,
                    "message": "無先前進度，從頭開始"
                }

            return {
                "should_resume": True,
                "remaining_stocks": remaining_items,
                "resume_from_index": completed_count, # 這裡只是一個估計值，供 UI 顯示用
                "already_processed": completed_count,
                "message": f"發現 {completed_count} 個已完成項目，將處理剩餘 {remaining_count} 個"
            }
            
        except Exception as e:
            logger.error(f"獲取續傳資訊失敗: {e}")
            # 出錯時安全起見，重跑所有
            return {
                "should_resume": False,
                "remaining_stocks": full_list,
                "resume_from_index": 0,
                "already_processed": 0,
                "message": f"讀取進度失敗，將從頭開始: {e}"
            }

    def mark_completed(self, collector_name: str, use_custom_range: bool = False):
        """
        標記收集器完成
        在 DB 模式下，update_progress 已經即時寫入，這裡可能不需要做特別的事。
        或者可以記錄一個特殊的 'ALL_DONE' 標記，但目前 Set-based 邏輯不需要。
        保留此方法以兼容舊代碼接口。
        """
        pass

    def reset_collector(self, collector_name: str):
        """重置單個收集器進度"""
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM collector_progress WHERE collector_name = %s", (collector_name,))
                    conn.commit()
            print(f"已重置收集器 {collector_name} 的進度")
        except Exception as e:
            print(f"重置進度失敗: {e}")

    def reset_all_progress(self):
        """重置所有收集器進度"""
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("TRUNCATE TABLE collector_progress")
                    conn.commit()
            print(f"已重置所有收集器的進度")
        except Exception as e:
            print(f"重置所有進度失敗: {e}")

    def show_status(self):
        """顯示所有收集器狀態"""
        print("\n" + "="*80)
        print("收集器進度狀態 (Database)")
        print("="*80)
        
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT collector_name, COUNT(*), MAX(updated_at)
                        FROM collector_progress 
                        WHERE status = 'DONE'
                        GROUP BY collector_name
                        ORDER BY collector_name
                    """)
                    rows = cursor.fetchall()
            
            if not rows:
                print("尚無任何收集器進度記錄")
                return

            for row in rows:
                name, count, last_updated = row
                print(f"\n[Collector]: {name}")
                print(f"   已處理項目: {count}")
                print(f"   最後更新: {last_updated}")
                
        except Exception as e:
            print(f"查詢狀態失敗: {e}")
            
        print("\n" + "="*80)
