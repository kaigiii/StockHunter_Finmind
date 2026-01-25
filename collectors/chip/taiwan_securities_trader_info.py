#!/usr/bin/env python3
"""
證券商資訊表數據收集器 / Taiwan Securities Trader Info Data Collector
專門負責收集台灣證券商資訊數據 / Specialized in collecting securities trader information data of Taiwan
API: TaiwanSecuritiesTraderInfo
"""

import logging
import pandas as pd
from datetime import datetime
from core.database import DatabaseManager
from collectors.base import BaseOneShotCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanSecuritiesTraderInfoCollector(BaseOneShotCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_securities_trader_info")
    
    def _call_api(self):
        """收集證券商資訊數據"""
        logger.info("開始收集證券商資訊數據...")
        
        # 從FinMind獲取證券商資訊
        df = self.api.taiwan_securities_trader_info()
        
        if df.empty:
            logger.warning("未獲取到證券商資訊數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆證券商資訊")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存證券商資訊到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info("無證券商資訊數據，跳過儲存")
            return True
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO securities_trader_info_data (
                securities_trader_id, securities_trader, date, address, phone, created_at
            )
            VALUES %s
            ON CONFLICT (securities_trader_id) 
            DO UPDATE SET 
                securities_trader = EXCLUDED.securities_trader,
                date = EXCLUDED.date,
                address = EXCLUDED.address,
                phone = EXCLUDED.phone,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                str(row.get('securities_trader_id', ''))[:20],  # 限制長度
                str(row.get('securities_trader', ''))[:200],  # 限制長度
                str(row.get('date', ''))[:20],  # 限制長度
                str(row.get('address', ''))[:500],  # 限制長度
                str(row.get('phone', ''))[:50],  # 限制長度
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"批次儲存 {len(data_rows)} 筆證券商資訊數據")
            return True
        else:
            logger.error("儲存證券商資訊數據失敗")
            return False
    
    def get_data(self):
        """從數據庫獲取證券商資訊"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM securities_trader_info_data ORDER BY securities_trader_id")
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取證券商資訊失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(rate_limiter=rate_limiter, progress_manager=progress_manager)
