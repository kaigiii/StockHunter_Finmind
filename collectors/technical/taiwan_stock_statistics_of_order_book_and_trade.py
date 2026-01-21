#!/usr/bin/env python3
"""
每5秒委託成交統計數據收集器 / Taiwan Stock Statistics Of Order Book And Trade Data Collector
專門負責收集台灣股市的委託成交統計資訊 / Specialized in collecting order book and trade statistics data of Taiwan stock market
API: TaiwanStockStatisticsOfOrderBookAndTrade
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from collectors.base import BaseDateListCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockStatisticsOfOrderBookAndTradeCollector(BaseDateListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_statistics_of_order_book_and_trade")
    
    def _call_api(self, date: str):
        """調用 FinMind API 獲取委託成交統計數據"""
        return self.api.taiwan_stock_book_and_trade(date=date)
    
    def _save_data(self, df, date: str) -> bool:
        """儲存委託成交統計數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"日期 {date} 無委託成交統計數據，跳過儲存")
            return True
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_statistics_of_order_book_and_trade_data (
                time, date, total_buy_order, total_buy_volume, 
                total_sell_order, total_sell_volume, total_deal_order,
                total_deal_volume, total_deal_money, created_at
            )
            VALUES %s
            ON CONFLICT (date, time) 
            DO UPDATE SET 
                total_buy_order = EXCLUDED.total_buy_order,
                total_buy_volume = EXCLUDED.total_buy_volume,
                total_sell_order = EXCLUDED.total_sell_order,
                total_sell_volume = EXCLUDED.total_sell_volume,
                total_deal_order = EXCLUDED.total_deal_order,
                total_deal_volume = EXCLUDED.total_deal_volume,
                total_deal_money = EXCLUDED.total_deal_money,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                row.get('Time'),
                row.get('date'),
                row.get('TotalBuyOrder'),
                row.get('TotalBuyVolume'),
                row.get('TotalSellOrder'),
                row.get('TotalSellVolume'),
                row.get('TotalDealOrder'),
                row.get('TotalDealVolume'),
                row.get('TotalDealMoney'),
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"日期 {date} 批次儲存 {len(data_rows)} 筆委託成交統計數據")
            return True
        else:
            logger.error(f"儲存日期 {date} 委託成交統計數據失敗")
            return False

    def get_data(self, start_date=None, end_date=None):
        """從數據庫獲取委託成交統計數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                if start_date and end_date:
                    query = """
                        SELECT * FROM stock_statistics_of_order_book_and_trade_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY date DESC, time DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_statistics_of_order_book_and_trade_data ORDER BY date DESC, time DESC"
                    cursor.execute(query)
                
                return cursor.fetchall()

    def main(self, start_date=None, end_date=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date=start_date, end_date=end_date, rate_limiter=rate_limiter, use_custom_range=use_custom_range, progress_manager=progress_manager)


def main():
    """主函數，執行委託成交統計資料收集"""
    collector = TaiwanStockStatisticsOfOrderBookAndTradeCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_ORDER_BOOK_TRADE_START_DATE', '2005-01-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success, message = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    if success:
        print(f"✅ 委託成交統計資料收集完成！")
        print(f"📊 結果: {message}")
    else:
        print(f"❌ 委託成交統計資料收集失敗: {message}")
