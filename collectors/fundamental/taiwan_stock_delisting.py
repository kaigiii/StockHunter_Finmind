#!/usr/bin/env python3
"""
台灣股票下市櫃表數據收集器 / Taiwan Stock Delisting Data Collector
專門負責收集台灣股票的下市櫃資訊 / Specialized in collecting delisting data of Taiwan stocks
API: TaiwanStockDelisting
"""

import logging
from datetime import datetime
from core.database import DatabaseManager
from collectors.base import BaseOneShotCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockDelistingCollector(BaseOneShotCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_delisting")
    
    def _call_api(self):
        """收集股票下市櫃資訊"""
        logger.info("開始收集台灣股票下市櫃資訊...")
        
        # 從FinMind獲取股票下市櫃資訊
        df = self.api.taiwan_stock_delisting()
        
        if df.empty:
            logger.warning("未獲取到股票下市櫃資訊數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆股票下市櫃資訊")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存股票下市櫃數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info("無股票下市櫃數據，跳過儲存")
            return True
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_delisting_data (
                delisting_date, stock_id, stock_name, created_at
            )
            VALUES %s
            ON CONFLICT (stock_id) 
            DO UPDATE SET 
                delisting_date = EXCLUDED.delisting_date,
                stock_name = EXCLUDED.stock_name,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                row.get('date'),
                row.get('stock_id'),
                row.get('stock_name'),
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"批次儲存 {len(data_rows)} 筆股票下市櫃數據")
            return True
        else:
            logger.error("儲存股票下市櫃數據失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取下市櫃數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            try:
                cursor = conn.cursor()
                
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_delisting_data 
                        WHERE stock_id = %s AND delisting_date BETWEEN %s AND %s 
                        ORDER BY delisting_date DESC
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_delisting_data 
                        WHERE stock_id = %s 
                        ORDER BY delisting_date DESC
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_delisting_data 
                        WHERE delisting_date BETWEEN %s AND %s 
                        ORDER BY delisting_date DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_delisting_data ORDER BY delisting_date DESC"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取下市櫃數據失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(rate_limiter=rate_limiter, progress_manager=progress_manager)
