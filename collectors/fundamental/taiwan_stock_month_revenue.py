#!/usr/bin/env python3
"""
月營收數據收集器 / Taiwan Stock Month Revenue Data Collector
專門負責收集台灣股票的月營收資訊 / Specialized in collecting monthly revenue data of Taiwan stocks
API: TaiwanStockMonthRevenue
"""

import logging
from datetime import datetime
from collectors.base import BaseStockListCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockMonthRevenueCollector(BaseStockListCollector):
    
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_month_revenue")
    
    def _call_api(self, stock_id, start_date, end_date):
        """調用 FinMind API 獲取月營收資訊"""
        return self.api.taiwan_stock_month_revenue(
            stock_id=stock_id,
            start_date=start_date
        )
    
    def _save_data(self, df, stock_id):
        """儲存月營收資料到資料庫"""
        if df.empty:
            logger.info(f"股票 {stock_id} 無月營收資訊，跳過儲存")
            return True
        
        # 準備批次插入資料
        insert_query = """
            INSERT INTO stock_month_revenue_data (
                date, stock_id, country, revenue, revenue_year, revenue_month, created_at
            )
            VALUES %s
            ON CONFLICT (stock_id, date)
            DO UPDATE SET
                country = EXCLUDED.country,
                revenue = EXCLUDED.revenue,
                revenue_year = EXCLUDED.revenue_year,
                revenue_month = EXCLUDED.revenue_month,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備資料清單 - 去除重複的 (stock_id, date)
        data_list = []
        seen_combinations = set()
        
        for _, row in df.iterrows():
            date = row.get('date')
            combination = (stock_id, date)
            
            # 跳過重複的 (stock_id, date) 組合
            if combination in seen_combinations:
                continue
            seen_combinations.add(combination)
            
            data_list.append((
                date,
                stock_id,
                row.get('country'),
                row.get('revenue'),
                row.get('revenue_year'),
                row.get('revenue_month'),
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_list):
            logger.info(f"批次儲存 {len(data_list)} 筆股票 {stock_id} 的月營收資料")
            return True
        else:
            logger.error(f"儲存股票 {stock_id} 月營收資料失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取月營收數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            try:
                cursor = conn.cursor()
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_month_revenue_data 
                        WHERE stock_id = %s AND date BETWEEN %s AND %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_month_revenue_data 
                        WHERE stock_id = %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_month_revenue_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY stock_id, date DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_month_revenue_data ORDER BY stock_id, date DESC"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取月營收數據失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return self.run(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            rate_limiter=rate_limiter,
            use_custom_range=use_custom_range,
            progress_manager=progress_manager
        )
