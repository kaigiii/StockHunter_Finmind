#!/usr/bin/env python3
"""
綜合損益表數據收集器 / Taiwan Stock Financial Statements Data Collector
專門負責收集台灣股票的綜合損益表資訊 / Specialized in collecting financial statements data of Taiwan stocks
API: TaiwanStockFinancialStatements
"""

import pandas as pd
import logging
from datetime import datetime
from base_collector import BaseStockListCollector
from psycopg2.extras import execute_values

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockFinancialStatementsCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_financial_statements")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """呼叫 FinMind API 獲取綜合損益表數據"""
        return self.api.taiwan_stock_financial_statement(
            stock_id=stock_id,
            start_date=start_date,
        )

    def _save_data(self, df, stock_id) -> bool:
        """儲存綜合損益表數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無綜合損益表數據，跳過儲存")
            return True
        
        conn = None
        try:
            stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
            
            # 使用連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error(f"無法獲取資料庫連線 - 股票 {stock_id_val}")
                return False
            
            cursor = conn.cursor()
            
            # 準備批次插入語句
            insert_query = """
                INSERT INTO stock_financial_statements_data (date, stock_id, type, value, origin_name, created_at)
                VALUES %s
                ON CONFLICT (date, stock_id, type) 
                DO UPDATE SET 
                    value = EXCLUDED.value,
                    origin_name = EXCLUDED.origin_name,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                data_rows.append((
                    row['date'],
                    stock_id_val,
                    row['type'],
                    row['value'],
                    row.get('origin_name', ''),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆綜合損益表數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            stock_id_val = df['stock_id'].iloc[0] if not df.empty and 'stock_id' in df.columns else stock_id
            logger.error(f"儲存股票 {stock_id_val} 綜合損益表數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取綜合損益表數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_financial_statements_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_financial_statements_data 
                    WHERE stock_id = %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_financial_statements_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_financial_statements_data ORDER BY stock_id, date DESC"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            return data
            
        except Exception as e:
            logger.error(f"獲取綜合損益表數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法"""
        return self.run(start_date=start_date, end_date=end_date, stock_list=stock_list, rate_limiter=rate_limiter, use_custom_range=use_custom_range, progress_manager=progress_manager)
