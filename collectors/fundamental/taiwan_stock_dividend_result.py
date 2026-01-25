#!/usr/bin/env python3
"""
除權除息結果表數據收集器 / Taiwan Stock Dividend Result Data Collector
專門負責收集台灣股票的除權除息結果資訊 / Specialized in collecting dividend result data of Taiwan stocks
API: TaiwanStockDividendResult
"""

import logging
import pandas as pd
from datetime import datetime
from collectors.base import BaseStockListCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockDividendResultCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_dividend_result")

    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """呼叫 FinMind API 獲取除權除息結果數據"""
        return self.api.taiwan_stock_dividend_result(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

    def _save_data(self, df: pd.DataFrame, stock_id: str) -> bool:
        """儲存除權除息結果數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無除權除息結果數據，跳過儲存")
            return True
        
        stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_dividend_result_data (
                date, stock_id, before_price, after_price, stock_and_cache_dividend,
                stock_or_cache_dividend, max_price, min_price, open_price, reference_price, created_at
            )
            VALUES %s
            ON CONFLICT (stock_id, date) 
            DO UPDATE SET 
                before_price = EXCLUDED.before_price,
                after_price = EXCLUDED.after_price,
                stock_and_cache_dividend = EXCLUDED.stock_and_cache_dividend,
                stock_or_cache_dividend = EXCLUDED.stock_or_cache_dividend,
                max_price = EXCLUDED.max_price,
                min_price = EXCLUDED.min_price,
                open_price = EXCLUDED.open_price,
                reference_price = EXCLUDED.reference_price,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                row.get('date'),
                row.get('stock_id'),
                row.get('before_price'),
                row.get('after_price'),
                row.get('stock_and_cache_dividend'),
                row.get('stock_or_cache_dividend'),
                row.get('max_price'),
                row.get('min_price'),
                row.get('open_price'),
                row.get('reference_price'),
                datetime.now()
            ))

        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆除權除息結果數據")
            return True
        else:
            logger.error(f"儲存股票 {stock_id_val} 除權除息結果數據失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取除權除息結果數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            try:
                cursor = conn.cursor()
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_dividend_result_data 
                        WHERE stock_id = %s AND date BETWEEN %s AND %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_dividend_result_data 
                        WHERE stock_id = %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_dividend_result_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY stock_id, date DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_dividend_result_data ORDER BY stock_id, date DESC"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取除權除息結果數據失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)
