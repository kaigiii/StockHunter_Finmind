#!/usr/bin/env python3
"""
台股分割後參考價數據收集器 / Taiwan Stock Split Price Data Collector
專門負責收集台灣股票的分割後參考價資訊 / Specialized in collecting split price data of Taiwan stocks
API: TaiwanStockSplitPrice
"""

import pandas as pd
import logging
from datetime import datetime
from FinMind.data import DataLoader
from core.database import DatabaseManager
from collectors.base import BaseOneShotCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockSplitPriceCollector(BaseOneShotCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_split_price")
    
    def _call_api(self):
        """收集股票分割後參考價資訊"""
        logger.info("開始收集台股分割後參考價資訊...")
        
        # 從FinMind獲取股票分割後參考價資訊
        try:
            df = self.api.get_data(dataset='TaiwanStockSplitPrice')
        except Exception as api_error:
            logger.error(f"API調用失敗: {api_error}")
            return pd.DataFrame()
        
        if df.empty:
            logger.warning("未獲取到股票分割後參考價資訊數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆股票分割後參考價資訊")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存股票分割後參考價數據到數據庫"""
        if df.empty:
            logger.warning("無股票分割後參考價數據可儲存")
            return True
        
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return False
            
            cursor = conn.cursor()
            
            # 準備批次插入語句
            insert_query = """
                INSERT INTO stock_split_price_data (
                    date, stock_id, type, before_price, after_price, 
                    max_price, min_price, open_price
                )
                VALUES %s
                ON CONFLICT (stock_id, date) 
                DO UPDATE SET 
                    type = EXCLUDED.type,
                    before_price = EXCLUDED.before_price,
                    after_price = EXCLUDED.after_price,
                    max_price = EXCLUDED.max_price,
                    min_price = EXCLUDED.min_price,
                    open_price = EXCLUDED.open_price,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次插入資料 - 去除重複的 (stock_id, date)
            data_list = []
            seen_combinations = set()
            
            for _, row in df.iterrows():
                stock_id = row.get('stock_id')
                date = row.get('date')
                combination = (stock_id, date)
                
                # 跳過重複的 (stock_id, date) 組合
                if combination in seen_combinations:
                    continue
                seen_combinations.add(combination)
                
                data_list.append((
                    date,
                    stock_id,
                    row.get('type'),
                    row.get('before_price'),
                    row.get('after_price'),
                    row.get('max_price'),
                    row.get('min_price'),
                    row.get('open_price')
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_list, page_size=1000)
            conn.commit()
            
            logger.info(f"批次儲存 {len(data_list)} 筆股票分割後參考價數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存股票分割後參考價數據失敗: {e}")
            return False
        finally:
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取分割後參考價數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_split_price_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_split_price_data 
                    WHERE stock_id = %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_split_price_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_split_price_data ORDER BY stock_id, date DESC"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取分割後參考價數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(rate_limiter=rate_limiter, progress_manager=progress_manager)
