#!/usr/bin/env python3
"""
證券借貸數據收集器 / Taiwan Stock Securities Lending Data Collector
專門負責收集台灣個股證券借貸數據 / Specialized in collecting securities lending data of Taiwan stocks
API: TaiwanStockSecuritiesLending
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from collectors.base import BaseStockListCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockSecuritiesLendingCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_securities_lending")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """調用 FinMind API 獲取證券借貸數據"""
        return self.api.taiwan_stock_securities_lending(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存證券借貸數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無證券借貸數據，跳過儲存")
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
                INSERT INTO stock_securities_lending_data (
                    date, stock_id, transaction_type, volume, fee_rate, 
                    close, original_return_date, original_lending_period
                )
                VALUES %s
                ON CONFLICT (stock_id, date, transaction_type, volume, fee_rate) 
                DO UPDATE SET 
                    close = EXCLUDED.close,
                    original_return_date = EXCLUDED.original_return_date,
                    original_lending_period = EXCLUDED.original_lending_period,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據 - 去除重複的約束組合
            data_rows = []
            seen_combinations = set()
            
            for _, row in df.iterrows():
                # 創建約束組合的鍵
                constraint_key = (
                    stock_id_val,
                    str(row.get('date')),
                    str(row.get('transaction_type', '')),
                    str(row.get('volume', 0)),
                    str(row.get('fee_rate', 0))
                )
                
                # 跳過重複的約束組合
                if constraint_key in seen_combinations:
                    continue
                seen_combinations.add(constraint_key)
                
                # 處理 original_return_date，將空字符串轉換為 None
                original_return_date = row.get('original_return_date')
                if original_return_date == '' or original_return_date is None:
                    original_return_date = None
                
                data_rows.append((
                    row.get('date'),
                    stock_id_val,
                    row.get('transaction_type', ''),
                    row.get('volume', 0),
                    row.get('fee_rate', 0),
                    row.get('close', 0),
                    original_return_date,
                    row.get('original_lending_period', 0)
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows, page_size=1000)
            conn.commit()
            
            cursor.close()
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆證券借貸數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            stock_id_val = df['stock_id'].iloc[0] if not df.empty and 'stock_id' in df.columns else stock_id
            logger.error(f"儲存股票 {stock_id_val} 證券借貸數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取證券借貸數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_securities_lending_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_securities_lending_data 
                    WHERE stock_id = %s 
                    ORDER BY date
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_securities_lending_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_securities_lending_data ORDER BY stock_id, date"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取證券借貸數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)


def main():
    """主函數，執行證券借貸資料收集"""
    collector = TaiwanStockSecuritiesLendingCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_SECURITIES_LENDING_START_DATE', '2003-01-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    total_processed, total_success = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    print(f"✅ 證券借貸資料收集完成！")
    print(f"📊 處理股票數量: {total_processed}")
    print(f"✅ 成功股票數量: {total_success}")
    print(f"❌ 失敗股票數量: {total_processed - total_success}")
