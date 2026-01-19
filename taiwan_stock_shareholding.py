#!/usr/bin/env python3
"""
外資持股表數據收集器 / Taiwan Stock Shareholding Data Collector
專門負責收集台灣個股外資持股數據 / Specialized in collecting foreign shareholding data of Taiwan stocks
API: TaiwanStockShareholding
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

class TaiwanStockShareholdingCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_shareholding")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """調用 FinMind API 獲取外資持股數據"""
        return self.api.taiwan_stock_shareholding(
            stock_id=stock_id,
            start_date=start_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存外資持股數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無外資持股數據，跳過儲存")
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
                INSERT INTO stock_shareholding_data (
                    date, stock_id, stock_name, internationalcode, 
                    foreigninvestmentremainingshares, foreigninvestmentshares, 
                    foreigninvestmentremainratio, foreigninvestmentsharesratio,
                    foreigninvestmentupperlimitratio, chineseinvestmentupperlimitratio,
                    numberofsharesissued, recentlydeclaredate, note, created_at
                )
                VALUES %s
                ON CONFLICT (stock_id, date) 
                DO UPDATE SET 
                    stock_name = EXCLUDED.stock_name,
                    internationalcode = EXCLUDED.internationalcode,
                    foreigninvestmentremainingshares = EXCLUDED.foreigninvestmentremainingshares,
                    foreigninvestmentshares = EXCLUDED.foreigninvestmentshares,
                    foreigninvestmentremainratio = EXCLUDED.foreigninvestmentremainratio,
                    foreigninvestmentsharesratio = EXCLUDED.foreigninvestmentsharesratio,
                    foreigninvestmentupperlimitratio = EXCLUDED.foreigninvestmentupperlimitratio,
                    chineseinvestmentupperlimitratio = EXCLUDED.chineseinvestmentupperlimitratio,
                    numberofsharesissued = EXCLUDED.numberofsharesissued,
                    recentlydeclaredate = EXCLUDED.recentlydeclaredate,
                    note = EXCLUDED.note,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                data_rows.append((
                    row.get('date'),
                    stock_id_val,
                    row.get('stock_name', ''),
                    row.get('InternationalCode', ''),
                    row.get('ForeignInvestmentRemainingShares', 0),
                    row.get('ForeignInvestmentShares', 0),
                    row.get('ForeignInvestmentRemainRatio', 0),
                    row.get('ForeignInvestmentSharesRatio', 0),
                    row.get('ForeignInvestmentUpperLimitRatio', 0),
                    row.get('ChineseInvestmentUpperLimitRatio', 0),
                    row.get('NumberOfSharesIssued', 0),
                    row.get('RecentlyDeclareDate', ''),
                    row.get('note', ''),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆外資持股數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            stock_id_val = df['stock_id'].iloc[0] if not df.empty and 'stock_id' in df.columns else stock_id
            logger.error(f"儲存股票 {stock_id_val} 外資持股數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取外資持股數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_shareholding_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_shareholding_data 
                    WHERE stock_id = %s 
                    ORDER BY date
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_shareholding_data 
                    WHERE date BETWEEN %s AND %s 
                    ORDER BY stock_id, date
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_shareholding_data ORDER BY stock_id, date"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取外資持股數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)


def main():
    """主函數，執行外資持股資料收集"""
    collector = TaiwanStockShareholdingCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_SHAREHOLDING_START_DATE', '2004-02-01')
    
    total_processed, total_success = collector.run(
        start_date=start_date,
        use_custom_range=False
    )
    
    print(f"✅ 外資持股資料收集完成！")
    print(f"📊 處理股票數量: {total_processed}")
    print(f"✅ 成功股票數量: {total_success}")
    print(f"❌ 失敗股票數量: {total_processed - total_success}")
