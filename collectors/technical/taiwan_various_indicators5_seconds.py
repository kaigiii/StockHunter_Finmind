#!/usr/bin/env python3
"""
加權指數數據收集器 / Taiwan Various Indicators 5Seconds Data Collector
專門負責收集台灣加權指數 (TAIEX) 數據 / Specialized in collecting Taiwan Weighted Index (TAIEX) data
API: TaiwanVariousIndicators5Seconds
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from collectors.base import BaseDateListCollector
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanVariousIndicators5SecondsCollector(BaseDateListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_various_indicators5_seconds")
    
    def _call_api(self, date: str):
        """調用 FinMind API 獲取加權指數數據"""
        return self.api.tse(date=date)
    
    def _save_data(self, df, date: str) -> bool:
        """儲存加權指數數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"日期 {date} 無加權指數數據，跳過儲存")
            return True
        
        conn = None
        try:
            # 使用連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error(f"無法獲取資料庫連線 - 日期 {date}")
                return False
            
            cursor = conn.cursor()
            
            # 準備批次插入語句
            insert_query = """
                INSERT INTO various_indicators5_seconds_data (date, TAIEX, created_at)
                VALUES %s
                ON CONFLICT (date) 
                DO UPDATE SET 
                    TAIEX = EXCLUDED.TAIEX,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                taiex_value = float(row.get('TAIEX', 0))
                data_rows.append((date, taiex_value, datetime.now()))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"日期 {date} 批次儲存 {len(data_rows)} 筆加權指數數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存日期 {date} 加權指數數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)
    
    def get_data(self, start_date=None, end_date=None):
        """從數據庫獲取加權指數數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if start_date and end_date:
                query = """
                    SELECT * FROM various_indicators5_seconds_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY date
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM various_indicators5_seconds_data ORDER BY date"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取加權指數數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date=start_date, end_date=end_date, rate_limiter=rate_limiter, use_custom_range=use_custom_range, progress_manager=progress_manager)


def main():
    """主函數，執行每5秒委託成交統計數據收集"""
    collector = TaiwanVariousIndicators5SecondsCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_VARIOUS_INDICATORS_START_DATE', '2005-10-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success, message = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    if success:
        print(f"✅ 加權指數資料收集完成！")
        print(f"📊 結果: {message}")
    else:
        print(f"❌ 加權指數資料收集失敗: {message}")


if __name__ == "__main__":
    main()
