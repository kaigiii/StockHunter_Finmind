
"""
Collector Progress Manager (Database Version)
Tracks the progress of data collectors using PostgreSQL to support robust concurrency.
"""

import logging
from typing import Dict, List
from core.database import DatabaseManager
from datetime import datetime

logger = logging.getLogger(__name__)

class CheckpointManager:
    """收集器進度管理器 (資料庫版)"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_collector_progress(self, collector_name: str, use_custom_range: bool = False) -> Dict:
        """獲取單個收集器進度統計"""
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
                "total_processed": count,
                "last_updated": last_updated
            }
        except Exception as e:
            logger.error(f"獲取進度失敗: {e}")
            return {"supports_resume": False, "error": str(e)}

    def update_progress(self, collector_name: str, use_custom_range: bool, 
                       item_id: str, global_index: int = 0, error_occurred: bool = False):
        """更新進度"""
        if use_custom_range or error_occurred:
            return
            
        try:
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
        """獲取續傳資訊"""
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT item_id 
                        FROM collector_progress 
                        WHERE collector_name = %s AND status = 'DONE'
                    """, (collector_name,))
                    rows = cursor.fetchall()
            
            completed_set = {row[0] for row in rows}
            
            # 檢查是否有全局完成標記 'ALL'
            if "ALL" in completed_set:
                return {
                    "should_resume": False,
                    "all_completed": True,
                    "remaining_stocks": [],
                    "already_processed": len(completed_set) - 1 if "ALL" in completed_set else len(completed_set)
                }

            remaining_items = [item for item in full_list if str(item) not in completed_set]
            
            return {
                "should_resume": len(remaining_items) > 0,
                "all_completed": len(remaining_items) == 0,
                "remaining_stocks": remaining_items,
                "already_processed": len(completed_set)
            }
        except Exception as e:
            logger.error(f"獲取續傳資訊失敗: {e}")
            return {"should_resume": False, "remaining_stocks": full_list}

    def get_all_collectors_status(self) -> Dict[str, Dict]:
        """獲取所有收集器的狀態摘要 (用於 Web Dashboard)"""
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT collector_name, COUNT(*), MAX(updated_at)
                        FROM collector_progress 
                        WHERE status = 'DONE'
                        GROUP BY collector_name
                    """)
                    rows = cursor.fetchall()
                    return {
                        row[0]: {
                            "count": row[1],
                            "last_update": row[2].strftime("%Y-%m-%d %H:%M") if row[2] else "無"
                        } for row in rows
                    }
        except Exception as e:
            logger.error(f"獲取全體狀態失敗: {e}")
            return {}

    def reset_collector(self, collector_name: str):
        """重置單個收集器進度"""
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM collector_progress WHERE collector_name = %s", (collector_name,))
                    conn.commit()
        except Exception as e:
            logger.error(f"重置進度失敗: {e}")

    def reset_all_progress(self):
        """重置所有收集器進度"""
        try:
            with self.db_manager.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("TRUNCATE TABLE collector_progress")
                    conn.commit()
        except Exception as e:
            logger.error(f"重置所有進度失敗: {e}")

    def mark_completed(self, collector_name: str, use_custom_range: bool = False):
        """標記收集器完成 (一次性任務調用)"""
        if use_custom_range:
            return
        # 對於 OneShot 任務，我們插入一個 'ALL' 作為標記
        self.update_progress(collector_name, False, "ALL")

    def show_status(self):
        """相容性接口：顯示狀態摘要"""
        status = self.get_all_collectors_status()
        print("\n=== 收集器進度統計 ===")
        for name, info in status.items():
            print(f"{name}: 已處理 {info['count']} 筆, 最後更新: {info['last_update']}")
