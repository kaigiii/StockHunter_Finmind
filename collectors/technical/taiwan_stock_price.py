#!/usr/bin/env python3
"""
股價日成交資訊數據收集器 / Taiwan Stock Price Data Collector
專門負責收集台灣股票的日線價格和成交量數據 / Specialized in collecting daily price and volume data of Taiwan stocks
API: TaiwanStockPrice
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from collectors.base import BaseStockListCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockPriceCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_price")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """調用 FinMind API 獲取股票日線數據"""
        return self.api.taiwan_stock_daily(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存股票價格數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無數據，跳過儲存")
            return True
        
        stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_price_data (
                stock_id, date, Trading_Volume, Trading_money, open, max, min, close, spread, Trading_turnover
            )
            VALUES %s
            ON CONFLICT (stock_id, date) 
            DO UPDATE SET 
                Trading_Volume = EXCLUDED.Trading_Volume,
                Trading_money = EXCLUDED.Trading_money,
                open = EXCLUDED.open,
                max = EXCLUDED.max,
                min = EXCLUDED.min,
                close = EXCLUDED.close,
                spread = EXCLUDED.spread,
                Trading_turnover = EXCLUDED.Trading_turnover
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                stock_id_val,
                row.get('date'),
                row.get('Trading_Volume', 0),
                row.get('Trading_money', 0),
                row.get('open', 0),
                row.get('max', 0),
                row.get('min', 0),
                row.get('close', 0),
                row.get('spread', 0),
                row.get('Trading_turnover', 0)
            ))
        
        # 使用 DatabaseManager 的 execute_batch 方法
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆價格數據")
            return True
        else:
            logger.error(f"儲存股票 {stock_id_val} 價格數據失敗")
            return False
            
    def get_data(self, stock_id, start_date=None, end_date=None):
        """從數據庫獲取股票數據"""
        query = ""
        params = ()
        
        if start_date and end_date:
            query = """
                SELECT * FROM stock_price_data 
                WHERE stock_id = %s AND date BETWEEN %s AND %s 
                ORDER BY date
            """
            params = (stock_id, start_date, end_date)
        else:
            query = "SELECT * FROM stock_price_data WHERE stock_id = %s ORDER BY date"
            params = (stock_id,)
            
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    
    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)


def main():
    """主函數，執行股票價格資料收集"""
    collector = TaiwanStockPriceCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_PRICE_START_DATE', '1994-10-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    total_processed, total_success = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    print(f"[Done] 股票價格資料收集完成！")
    print(f"處理股票數量: {total_processed}")
    print(f"[Success] 成功股票數量: {total_success}")
    print(f"[Failed] 失敗股票數量: {total_processed - total_success}")
