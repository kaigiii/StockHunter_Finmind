#!/usr/bin/env python3
"""
台灣市場整體法人買賣表數據收集器 / Taiwan Stock Total Institutional Investors Data Collector
專門負責收集台灣市場整體法人買賣數據 / Specialized in collecting total institutional investors data of Taiwan market
API: TaiwanStockTotalInstitutionalInvestors
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from collectors.base import BaseDateRangeCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockTotalInstitutionalInvestorsCollector(BaseDateRangeCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_total_institutional_investors")
        self.table_name = "taiwan_stock_total_institutional_investors"
        self.table_schema = """(
            date DATE,
            buy DECIMAL(20, 2),
            sell DECIMAL(20, 2),
            name VARCHAR(255),
            PRIMARY KEY (date, name)
        )"""
    
    def _call_api(self, start_date, end_date):
        """呼叫 API 獲取數據"""
        return self.api.taiwan_stock_institutional_investors_total(
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, data):
        """保存數據到資料庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if data.empty:
            logger.info("無台灣市場整體法人買賣數據，跳過儲存")
            return 0
        
        conn = None
        try:
            data = data.copy()
            data['date'] = pd.to_datetime(data['date']).dt.date
            
            # 根據欄位調整數據
            required_columns = ['date', 'buy', 'sell', 'name']
            if not all(col in data.columns for col in required_columns):
                logger.error("數據缺少必要欄位")
                return 0
            
            # 確保數值欄位格式正確
            data['buy'] = pd.to_numeric(data['buy'], errors='coerce')
            data['sell'] = pd.to_numeric(data['sell'], errors='coerce')
            
            # 使用連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return 0
            
            cursor = conn.cursor()
            
            # 準備批次插入語句
            insert_query = """
                INSERT INTO stock_total_institutional_investors_data (
                    date, name, buy, sell, created_at
                )
                VALUES %s
                ON CONFLICT (date, name) 
                DO UPDATE SET 
                    buy = EXCLUDED.buy,
                    sell = EXCLUDED.sell,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in data.iterrows():
                data_rows.append((
                    row.get('date'),
                    row.get('name'),
                    row.get('buy', 0),
                    row.get('sell', 0),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"批次儲存 {len(data_rows)} 筆台灣市場整體法人買賣數據")
            return len(data_rows)
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存台灣市場整體法人買賣數據失敗: {e}")
            return 0
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, start_date=None, end_date=None, name=None):
        """從數據庫獲取台灣市場整體法人買賣數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if start_date and end_date and name:
                query = """
                    SELECT * FROM stock_total_institutional_investors_data 
                    WHERE date BETWEEN %s AND %s AND name = %s
                    ORDER BY date DESC
                """
                cursor.execute(query, (start_date, end_date, name))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_total_institutional_investors_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY date DESC, name
                """
                cursor.execute(query, (start_date, end_date))
            elif name:
                query = """
                    SELECT * FROM stock_total_institutional_investors_data 
                    WHERE name = %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (name,))
            else:
                query = "SELECT * FROM stock_total_institutional_investors_data ORDER BY date DESC, name"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取台灣市場整體法人買賣數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(use_custom_range=use_custom_range, rate_limiter=rate_limiter, progress_manager=progress_manager)


def main():
    """主函數，執行台灣市場整體法人買賣資料收集"""
    collector = TaiwanStockTotalInstitutionalInvestorsCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_TOTAL_INSTITUTIONAL_INVESTORS_START_DATE', '2004-02-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success, message = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    if success:
        print(f"✅ 台灣市場整體法人買賣資料收集完成！")
        print(f"📊 結果: {message}")
    else:
        print(f"❌ 台灣市場整體法人買賣資料收集失敗: {message}")


if __name__ == "__main__":
    main()
