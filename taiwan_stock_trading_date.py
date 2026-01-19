#!/usr/bin/env python3
"""
台股交易日數據收集器 / Taiwan Stock Trading Date Data Collector
專門負責收集台灣股市的交易日資訊 / Specialized in collecting Taiwan stock market trading date information
API: TaiwanStockTradingDate
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from base_collector import BaseDateRangeCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('config.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockTradingDateCollector(BaseDateRangeCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_trading_date")
    
    def _call_api(self, start_date, end_date):
        """呼叫 API 獲取數據"""
        return self.api.taiwan_stock_trading_date(
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, data):
        """保存數據到資料庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if data.empty:
            logger.info("無交易日數據，跳過儲存")
            return 0
        
        conn = None
        try:
            data = data.copy()
            data['date'] = pd.to_datetime(data['date']).dt.date
            
            # API只返回 date 欄位，所有返回的都是交易日
            if 'date' not in data.columns:
                logger.error("數據缺少 date 欄位")
                return 0
            
            # 使用連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return 0
            
            cursor = conn.cursor()
            
            # 準備批次插入語句 - 只插入 date
            insert_query = """
                INSERT INTO stock_trading_date_data (
                    date, created_at
                )
                VALUES %s
                ON CONFLICT (date) 
                DO UPDATE SET 
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據 - 去除重複日期
            data_rows = []
            seen_dates = set()
            
            for _, row in data.iterrows():
                date_val = row.get('date')
                if date_val in seen_dates:
                    continue
                seen_dates.add(date_val)
                
                data_rows.append((
                    date_val,
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows, page_size=1000)
            conn.commit()
            
            cursor.close()
            logger.info(f"批次儲存 {len(data_rows)} 筆交易日數據")
            return len(data_rows)
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存交易日數據失敗: {e}")
            return 0
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, start_date=None, end_date=None):
        """從數據庫獲取交易日數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if start_date and end_date:
                query = """
                    SELECT * FROM stock_trading_date_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY date ASC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_trading_date_data ORDER BY date ASC"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取交易日數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_trading_dates_list(self, start_date=None, end_date=None):
        """獲取交易日期列表，用於其他收集器遍歷"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # 查詢交易日期（表中存儲的都是交易日）
            if start_date and end_date:
                query = """
                    SELECT date FROM stock_trading_date_data 
                    WHERE date BETWEEN %s AND %s
                    ORDER BY date ASC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT date FROM stock_trading_date_data ORDER BY date ASC"
                cursor.execute(query)
            
            # 獲取日期列表
            result = cursor.fetchall()
            dates = []
            for row in result:
                # row是一個tuple，日期在第一個位置
                date_val = row[0]
                if isinstance(date_val, str):
                    dates.append(date_val)
                else:
                    # 如果是datetime對象，轉換為字符串
                    dates.append(date_val.strftime('%Y-%m-%d'))
            
            cursor.close()
            
            return dates
            
        except Exception as e:
            logger.error(f"獲取交易日期列表失敗: {e}")
            return []
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(use_custom_range=use_custom_range, rate_limiter=rate_limiter, progress_manager=progress_manager)


def main():
    """主函數，執行交易日資料收集"""
    collector = TaiwanStockTradingDateCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_TRADING_DATE_START_DATE', '2001-01-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success, message = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    if success:
        print(f"✅ 交易日資料收集完成！")
        print(f"📊 結果: {message}")
    else:
        print(f"❌ 交易日資料收集失敗: {message}")


if __name__ == "__main__":
    main()
