#!/usr/bin/env python3
"""
法人買賣表數據收集器 / Taiwan Stock Institutional Investors Buy Sell Data Collector
專門負責收集台灣個股法人買賣數據 / Specialized in collecting institutional investors buy/sell data of Taiwan stocks
API: TaiwanStockInstitutionalInvestorsBuySell
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from base_collector import BaseStockListCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('config.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockInstitutionalInvestorsBuySellCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_institutional_investors_buy_sell")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """調用 FinMind API 獲取個股法人買賣數據"""
        return self.api.taiwan_stock_institutional_investors(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存個股法人買賣數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無法人買賣數據，跳過儲存")
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
                INSERT INTO stock_institutional_investors_buy_sell_data (
                    stock_id, date, name, buy, sell, created_at
                )
                VALUES %s
                ON CONFLICT (stock_id, date, name) 
                DO UPDATE SET 
                    buy = EXCLUDED.buy,
                    sell = EXCLUDED.sell,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                data_rows.append((
                    stock_id_val,
                    row.get('date'),
                    str(row.get('name', ''))[:200],  # 限制name欄位長度
                    row.get('buy', 0),
                    row.get('sell', 0),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆法人買賣數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            stock_id_val = df['stock_id'].iloc[0] if not df.empty and 'stock_id' in df.columns else stock_id
            logger.error(f"儲存股票 {stock_id_val} 法人買賣數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)
    
    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取個股法人買賣數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_institutional_investors_buy_sell_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date, name
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_institutional_investors_buy_sell_data 
                    WHERE stock_id = %s 
                    ORDER BY date, name
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_institutional_investors_buy_sell_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date, name
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_institutional_investors_buy_sell_data ORDER BY stock_id, date, name"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            return data
            
        except Exception as e:
            logger.error(f"獲取個股法人買賣數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)


def main():
    """主函數，執行個股法人買賣資料收集"""
    collector = TaiwanStockInstitutionalInvestorsBuySellCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_INSTITUTIONAL_INVESTORS_BUY_SELL_START_DATE', '2005-01-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    total_processed, total_success = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    print(f"✅ 個股法人買賣資料收集完成！")
    print(f"📊 處理股票數量: {total_processed}")
    print(f"✅ 成功股票數量: {total_success}")
    print(f"❌ 失敗股票數量: {total_processed - total_success}")
