#!/usr/bin/env python3
"""
台股總覽(含權證)數據收集器 / Taiwan Stock Info With Warrant Data Collector
專門負責收集台灣股票總覽資訊(包含權證) / Specialized in collecting Taiwan stock overview information including warrants
API: TaiwanStockInfoWithWarrant
"""

import pandas as pd
import logging
from datetime import datetime
from core.database import DatabaseManager
from collectors.base import BaseOneShotCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockInfoWithWarrantCollector(BaseOneShotCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_info_with_warrant")
    
    def _call_api(self):
        """收集台股總覽(含權證)數據"""
        logger.info("開始收集台股總覽(含權證)資訊...")
        
        # 從FinMind獲取台股總覽(含權證)數據
        df = self.api.taiwan_stock_info_with_warrant()
        
        if df.empty:
            logger.warning("未獲取到台股總覽(含權證)數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆台股總覽(含權證)數據")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存台股總覽(含權證)數據到數據庫"""
        if df.empty:
            logger.warning("無台股總覽(含權證)數據可儲存")
            return True
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_info_with_warrant_data (
                industry_category, stock_id, stock_name, type, date, created_at
            )
            VALUES %s
            ON CONFLICT (stock_id) 
            DO UPDATE SET 
                industry_category = EXCLUDED.industry_category,
                stock_name = EXCLUDED.stock_name,
                type = EXCLUDED.type,
                date = EXCLUDED.date,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次插入資料 - 去除重複的 stock_id
        data_list = []
        seen_stock_ids = set()
        
        for _, row in df.iterrows():
            stock_id = row.get('stock_id')
            
            # 跳過重複的 stock_id
            if stock_id in seen_stock_ids:
                continue
            seen_stock_ids.add(stock_id)
            
            data_list.append((
                str(row.get('industry_category', ''))[:200],
                stock_id,
                str(row.get('stock_name', ''))[:200],
                str(row.get('type', ''))[:50],
                row.get('date'),
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_list, page_size=1000):
            logger.info(f"批次儲存 {len(data_list)} 筆台股總覽(含權證)數據")
            return True
        else:
            logger.error("儲存台股總覽(含權證)數據失敗")
            return False

    def get_data(self, stock_id=None, stock_type=None):
        """從數據庫獲取台股總覽(含權證)數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                if stock_id:
                    query = """
                        SELECT * FROM stock_info_with_warrant_data 
                        WHERE stock_id = %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id,))
                elif stock_type:
                    query = """
                        SELECT * FROM stock_info_with_warrant_data 
                        WHERE type = %s 
                        ORDER BY stock_id
                    """
                    cursor.execute(query, (stock_type,))
                else:
                    query = "SELECT * FROM stock_info_with_warrant_data ORDER BY type, stock_id"
                    cursor.execute(query)
                
                return cursor.fetchall()
    
    def get_stock_list_with_warrant(self, stock_type=None):
        """獲取股票列表(含權證)"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return []
            
            with conn.cursor() as cursor:
                if stock_type:
                    query = "SELECT DISTINCT stock_id FROM stock_info_with_warrant_data WHERE type = %s ORDER BY stock_id"
                    cursor.execute(query, (stock_type,))
                else:
                    query = "SELECT DISTINCT stock_id FROM stock_info_with_warrant_data ORDER BY stock_id"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                return [row[0] for row in data] if data else []

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(rate_limiter=rate_limiter, progress_manager=progress_manager)
