#!/usr/bin/env python3
"""
台灣市場整體融資融劵表數據收集器 / Taiwan Stock Total Margin Purchase Short Sale Data Collector
專門負責收集台灣市場整體融資融券數據 / Specialized in collecting total margin purchase and short sale data of Taiwan market
API: TaiwanStockTotalMarginPurchaseShortSale
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
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

class TaiwanStockTotalMarginPurchaseShortSaleCollector(BaseDateRangeCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_total_margin_purchase_short_sale")
    
    def _call_api(self, start_date, end_date):
        """收集總融資融券數據"""
        logger.info(f"開始收集台灣市場整體融資融券數據...")
        logger.info(f"時間範圍: {start_date} 到 {end_date}")
        
        # 從FinMind獲取整體融資融券數據
        df = self.api.taiwan_stock_margin_purchase_short_sale_total(
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            logger.warning("無整體融資融券數據")
            return pd.DataFrame()
        
        logger.info(f"獲取到 {len(df)} 筆整體融資融券數據")
        return df
    
    def _save_data(self, df) -> bool:
        """儲存台灣市場整體融資融券數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info("無台灣市場整體融資融券數據，跳過儲存")
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
                INSERT INTO stock_total_margin_purchase_short_sale_data (
                    date, name, TodayBalance, YesBalance, buy, Return, sell, created_at
                )
                VALUES %s
                ON CONFLICT (date, name) 
                DO UPDATE SET 
                    TodayBalance = EXCLUDED.TodayBalance,
                    YesBalance = EXCLUDED.YesBalance,
                    buy = EXCLUDED.buy,
                    Return = EXCLUDED.Return,
                    sell = EXCLUDED.sell,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                data_rows.append((
                    row.get('date'),
                    str(row.get('name', ''))[:200],  # 限制name欄位長度
                    row.get('TodayBalance', 0),
                    row.get('YesBalance', 0),
                    row.get('buy', 0),
                    row.get('Return', 0),
                    row.get('sell', 0),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"批次儲存 {len(data_rows)} 筆台灣市場整體融資融券數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存台灣市場整體融資融券數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)
    
    def get_data(self, start_date=None, end_date=None):
        """從數據庫獲取台灣市場整體融資融券數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if start_date and end_date:
                query = """
                    SELECT * FROM stock_total_margin_purchase_short_sale_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY date, name
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_total_margin_purchase_short_sale_data ORDER BY date, name"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取台灣市場整體融資融券數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(use_custom_range=use_custom_range, rate_limiter=rate_limiter, progress_manager=progress_manager)
    

