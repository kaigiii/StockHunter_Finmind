#!/usr/bin/env python3
"""
台股總覽數據收集器 / Taiwan Stock Info Data Collector
專門負責收集台灣股票的基本資訊 / Specialized in collecting basic information of Taiwan stocks
API: TaiwanStockInfo
"""

import pandas as pd
import logging
from datetime import datetime
from FinMind.data import DataLoader
from core.database import DatabaseManager
from collectors.base import BaseOneShotCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockInfoCollector(BaseOneShotCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_info")
    
    def _call_api(self):
        """收集股票基本資訊"""
        logger.info("開始收集台股總覽資訊...")
        logger.info("📅 股票基本資訊無時間限制，獲取最新資料")
        
        # 從FinMind獲取股票資訊
        df = self.api.taiwan_stock_info()
        
        if df.empty:
            logger.warning("未獲取到股票資訊數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆股票資訊")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存股票基本資訊到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info("無股票基本資訊數據，跳過儲存")
            return True
            
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_info_data (
                stock_id, stock_name, industry_category, type, date, created_at
            )
            VALUES %s
            ON CONFLICT (stock_id) 
            DO UPDATE SET 
                stock_name = EXCLUDED.stock_name,
                industry_category = EXCLUDED.industry_category,
                type = EXCLUDED.type,
                date = EXCLUDED.date,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據 - 去除重複的 stock_id
        data_rows = []
        seen_stock_ids = set()
        
        for _, row in df.iterrows():
            # 處理實際API回傳的欄位
            stock_id = str(row.get('stock_id', ''))[:int(os.getenv('STOCK_ID_MAX_LENGTH', '20'))]
            
            # 跳過重複的 stock_id
            if stock_id in seen_stock_ids:
                continue
            seen_stock_ids.add(stock_id)
            
            stock_name = str(row.get('stock_name', ''))[:int(os.getenv('STOCK_NAME_MAX_LENGTH', '200'))]
            industry_category = str(row.get('industry_category', ''))[:int(os.getenv('INDUSTRY_CATEGORY_MAX_LENGTH', '200'))]
            type_val = str(row.get('type', ''))[:int(os.getenv('TYPE_MAX_LENGTH', '50'))]
            date_val = str(row.get('date', ''))[:int(os.getenv('DATE_MAX_LENGTH', '20'))]
            
            data_rows.append((
                stock_id, stock_name, industry_category, type_val, date_val, datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"批次儲存 {len(data_rows)} 筆股票基本資訊數據")
            return True
        else:
            logger.error("儲存股票基本資訊數據失敗")
            return False
    
    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取股票基本資訊"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                if stock_id:
                    query = """
                        SELECT * FROM stock_info_data 
                        WHERE stock_id = %s
                    """
                    cursor.execute(query, (stock_id,))
                else:
                    query = "SELECT * FROM stock_info_data ORDER BY stock_id"
                    cursor.execute(query)
                
                return cursor.fetchall()

    def get_stock_list(self):
        """獲取股票列表（用於其他收集器）"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return []
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT stock_id FROM stock_info_data ORDER BY stock_id")
                stocks = [row[0] for row in cursor.fetchall()]
                return stocks

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(rate_limiter=rate_limiter, progress_manager=progress_manager)


