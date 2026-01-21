#!/usr/bin/env python3
"""
個股PER、PBR資料表數據收集器 / Taiwan Stock PER Data Collector
專門負責收集台灣股票的本益比和股價淨值比資訊 / Specialized in collecting P/E ratio and P/B ratio data of Taiwan stocks
API: TaiwanStockPER
"""

import pandas as pd
import logging
from collectors.base import BaseStockListCollector

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockPerCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_per")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """呼叫 FinMind API 獲取 PER、PBR 數據"""
        return self.api.get_data(
            dataset='TaiwanStockPER',
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存PER、PBR數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無PER、PBR數據，跳過儲存")
            return True
        
        stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_per_data (
                date, stock_id, dividend_yield, per, pbr
            )
            VALUES %s
            ON CONFLICT (stock_id, date) 
            DO UPDATE SET 
                dividend_yield = EXCLUDED.dividend_yield,
                per = EXCLUDED.per,
                pbr = EXCLUDED.pbr,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                row.get('date'),
                stock_id_val,
                row.get('dividend_yield'),
                row.get('PER'),
                row.get('PBR')
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆PER、PBR數據")
            return True
        else:
            logger.error(f"儲存股票 {stock_id_val} PER、PBR數據失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取PER、PBR數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_per_data 
                        WHERE stock_id = %s AND date BETWEEN %s AND %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_per_data 
                        WHERE stock_id = %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_per_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY stock_id, date DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_per_data ORDER BY stock_id, date DESC"
                    cursor.execute(query)
                
                return cursor.fetchall()

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)
