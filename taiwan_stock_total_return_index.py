#!/usr/bin/env python3
"""
加權、櫃買報酬指數數據收集器 / Taiwan Stock Total Return Index Data Collector
專門負責收集台灣股市的報酬指數資訊 / Specialized in collecting total return index data of Taiwan stock market
API: TaiwanStockTotalReturnIndex
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

class TaiwanStockTotalReturnIndexCollector(BaseDateRangeCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_total_return_index")
        self.table_name = "taiwan_stock_total_return_index"
        self.table_schema = """(
            date DATE,
            stock_id VARCHAR(20),
            price DECIMAL(20, 6),
            PRIMARY KEY (date, stock_id)
        )"""
        # 預設的指數ID列表
        self.index_ids = ['TAIEX', 'TPEx']  # 加權指數和櫃買指數
    
    def _call_api(self, start_date, end_date):
        """呼叫 API 獲取數據 - 需要指定 index_id"""
        all_data = []
        
        for index_id in self.index_ids:
            try:
                df = self.api.taiwan_stock_total_return_index(
                    index_id=index_id,
                    start_date=start_date,
                    end_date=end_date
                )
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"獲取指數 {index_id} 數據失敗: {e}")
                continue
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _save_data(self, data):
        """保存數據到資料庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if data.empty:
            logger.info("無報酬指數數據，跳過儲存")
            return 0
        
        conn = None
        try:
            data = data.copy()
            data['date'] = pd.to_datetime(data['date']).dt.date
            
            # 根據 FinMind API 文檔，回傳欄位為：price, stock_id, date
            required_columns = ['date', 'stock_id', 'price']
            if not all(col in data.columns for col in required_columns):
                logger.error("數據缺少必要欄位")
                return 0
            
            # 只保留需要的欄位
            data = data[required_columns].copy()
            
            # 確保數值欄位格式正確
            data['price'] = pd.to_numeric(data['price'], errors='coerce')
            
            # 使用連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return 0
            
            cursor = conn.cursor()
            
            # 準備批次插入語句
            insert_query = """
                INSERT INTO stock_total_return_index_data (
                    date, stock_id, price, created_at
                )
                VALUES %s
                ON CONFLICT (date, stock_id) 
                DO UPDATE SET 
                    price = EXCLUDED.price,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in data.iterrows():
                data_rows.append((
                    row.get('date'),
                    row.get('stock_id'),
                    row.get('price'),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"批次儲存 {len(data_rows)} 筆報酬指數數據")
            return len(data_rows)
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"儲存報酬指數數據失敗: {e}")
            return 0
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取報酬指數數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_total_return_index_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_total_return_index_data 
                    WHERE stock_id = %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_total_return_index_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_total_return_index_data ORDER BY stock_id, date DESC"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取報酬指數數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法，供 main.py 調用"""
        return super().main(use_custom_range=use_custom_range, rate_limiter=rate_limiter, progress_manager=progress_manager)


def main():
    """主函數，執行報酬指數資料收集"""
    collector = TaiwanStockTotalReturnIndexCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_TOTAL_RETURN_INDEX_START_DATE', '2003-12-29')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success, message = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    if success:
        print(f"✅ 報酬指數資料收集完成！")
        print(f"📊 結果: {message}")
    else:
        print(f"❌ 報酬指數資料收集失敗: {message}")


if __name__ == "__main__":
    main()