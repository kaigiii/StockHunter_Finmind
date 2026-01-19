#!/usr/bin/env python3
"""
台股變更面額恢復買賣參考價格數據收集器 / Taiwan Stock Par Value Change Data Collector
專門負責收集台灣股票的變更面額恢復買賣參考價格資訊 / Specialized in collecting par value change reference price data of Taiwan stocks
API: TaiwanStockParValueChange
"""

import pandas as pd
import logging
from datetime import datetime
from FinMind.data import DataLoader
from database_setup import DatabaseManager
from base_collector import BaseDateRangeCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('config.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockParValueChangeCollector(BaseDateRangeCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_par_value_change")
    
    def _call_api(self, start_date, end_date):
        """收集股票變更面額恢復買賣參考價格資訊"""
        logger.info("開始收集台股變更面額恢復買賣參考價格資訊...")
        logger.info(f"📅 時間範圍: {start_date} ~ {end_date}")
        
        # 從FinMind獲取股票變更面額恢復買賣參考價格資訊
        try:
            df = self.api.get_data(
                dataset='TaiwanStockParValueChange',
                start_date=start_date,
                end_date=end_date
            )
        except Exception as api_error:
            logger.error(f"API調用失敗: {api_error}")
            return pd.DataFrame()
        
        if df.empty:
            logger.warning("未獲取到股票變更面額恢復買賣參考價格資訊數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆股票變更面額恢復買賣參考價格資訊")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存股票變更面額恢復買賣參考價格數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info("無股票變更面額恢復買賣參考價格數據，跳過儲存")
            return True
        
        conn = None
        try:
            # 使用連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return False
            
            cursor = conn.cursor()
            
            # 準備批次插入語句
            insert_query = """
                INSERT INTO stock_par_value_change_data (
                    date, stock_id, stock_name, before_close, after_ref_close, 
                    after_ref_max, after_ref_min, after_ref_open, created_at
                )
                VALUES %s
                ON CONFLICT (stock_id, date) 
                DO UPDATE SET 
                    stock_name = EXCLUDED.stock_name,
                    before_close = EXCLUDED.before_close,
                    after_ref_close = EXCLUDED.after_ref_close,
                    after_ref_max = EXCLUDED.after_ref_max,
                    after_ref_min = EXCLUDED.after_ref_min,
                    after_ref_open = EXCLUDED.after_ref_open,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                data_rows.append((
                    row.get('date'),
                    row.get('stock_id'),
                    row.get('stock_name'),
                    row.get('before_close'),
                    row.get('after_ref_close'),
                    row.get('after_ref_max'),
                    row.get('after_ref_min'),
                    row.get('after_ref_open'),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"批次儲存 {len(data_rows)} 筆股票變更面額恢復買賣參考價格數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存股票變更面額恢復買賣參考價格數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取變更面額恢復買賣參考價格數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_par_value_change_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_par_value_change_data 
                    WHERE stock_id = %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_par_value_change_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_par_value_change_data ORDER BY stock_id, date DESC"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取變更面額恢復買賣參考價格數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(use_custom_range=use_custom_range, rate_limiter=rate_limiter, progress_manager=progress_manager)
