#!/usr/bin/env python3
"""
股利政策表數據收集器 / Taiwan Stock Dividend Data Collector
專門負責收集台灣股票的股利政策資訊 / Specialized in collecting dividend policy data of Taiwan stocks
API: TaiwanStockDividend
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

class TaiwanStockDividendCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_dividend")
    
    def _call_api(self, stock_id, start_date, end_date):
        """調用 FinMind API 獲取股利政策資訊"""
        return self.api.taiwan_stock_dividend(
            stock_id=stock_id,
            start_date=start_date
        )
    
    def _save_data(self, df, stock_id):
        """儲存股利政策資料到資料庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無股利政策數據，跳過儲存")
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
                INSERT INTO stock_dividend_data (
                    date, stock_id, year, StockEarningsDistribution, StockStatutorySurplus, 
                    StockExDividendTradingDate, TotalEmployeeStockDividend, TotalEmployeeStockDividendAmount, 
                    RatioOfEmployeeStockDividendOfTotal, RatioOfEmployeeStockDividend, CashEarningsDistribution, 
                    CashStatutorySurplus, CashExDividendTradingDate, CashDividendPaymentDate, 
                    TotalEmployeeCashDividend, TotalNumberOfCashCapitalIncrease, CashIncreaseSubscriptionRate, 
                    CashIncreaseSubscriptionpRrice, RemunerationOfDirectorsAndSupervisors, 
                    ParticipateDistributionOfTotalShares, AnnouncementDate, AnnouncementTime, created_at
                )
                VALUES %s
                ON CONFLICT (stock_id, date, year) 
                DO UPDATE SET 
                    StockEarningsDistribution = EXCLUDED.StockEarningsDistribution,
                    StockStatutorySurplus = EXCLUDED.StockStatutorySurplus,
                    StockExDividendTradingDate = EXCLUDED.StockExDividendTradingDate,
                    TotalEmployeeStockDividend = EXCLUDED.TotalEmployeeStockDividend,
                    TotalEmployeeStockDividendAmount = EXCLUDED.TotalEmployeeStockDividendAmount,
                    RatioOfEmployeeStockDividendOfTotal = EXCLUDED.RatioOfEmployeeStockDividendOfTotal,
                    RatioOfEmployeeStockDividend = EXCLUDED.RatioOfEmployeeStockDividend,
                    CashEarningsDistribution = EXCLUDED.CashEarningsDistribution,
                    CashStatutorySurplus = EXCLUDED.CashStatutorySurplus,
                    CashExDividendTradingDate = EXCLUDED.CashExDividendTradingDate,
                    CashDividendPaymentDate = EXCLUDED.CashDividendPaymentDate,
                    TotalEmployeeCashDividend = EXCLUDED.TotalEmployeeCashDividend,
                    TotalNumberOfCashCapitalIncrease = EXCLUDED.TotalNumberOfCashCapitalIncrease,
                    CashIncreaseSubscriptionRate = EXCLUDED.CashIncreaseSubscriptionRate,
                    CashIncreaseSubscriptionpRrice = EXCLUDED.CashIncreaseSubscriptionpRrice,
                    RemunerationOfDirectorsAndSupervisors = EXCLUDED.RemunerationOfDirectorsAndSupervisors,
                    ParticipateDistributionOfTotalShares = EXCLUDED.ParticipateDistributionOfTotalShares,
                    AnnouncementDate = EXCLUDED.AnnouncementDate,
                    AnnouncementTime = EXCLUDED.AnnouncementTime,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # 準備批次數據
            data_rows = []
            for _, row in df.iterrows():
                data_rows.append((
                    row.get('date'),
                    stock_id_val,
                    row.get('year'),
                    row.get('StockEarningsDistribution', 0),
                    row.get('StockStatutorySurplus', 0),
                    row.get('StockExDividendTradingDate', ''),
                    row.get('TotalEmployeeStockDividend', 0),
                    row.get('TotalEmployeeStockDividendAmount', 0),
                    row.get('RatioOfEmployeeStockDividendOfTotal', 0),
                    row.get('RatioOfEmployeeStockDividend', 0),
                    row.get('CashEarningsDistribution', 0),
                    row.get('CashStatutorySurplus', 0),
                    row.get('CashExDividendTradingDate', ''),
                    row.get('CashDividendPaymentDate', ''),
                    row.get('TotalEmployeeCashDividend', 0),
                    row.get('TotalNumberOfCashCapitalIncrease', 0),
                    row.get('CashIncreaseSubscriptionRate', 0),
                    row.get('CashIncreaseSubscriptionpRrice', 0),
                    row.get('RemunerationOfDirectorsAndSupervisors', 0),
                    row.get('ParticipateDistributionOfTotalShares', 0),
                    row.get('AnnouncementDate', ''),
                    row.get('AnnouncementTime', ''),
                    datetime.now()
                ))
            
            # 執行批次插入
            execute_values(cursor, insert_query, data_rows)
            conn.commit()
            
            cursor.close()
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆股利政策數據")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            stock_id_val = df['stock_id'].iloc[0] if not df.empty and 'stock_id' in df.columns else stock_id
            logger.error(f"儲存股票 {stock_id_val} 股利政策數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取股利政策數據"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            if stock_id and start_date and end_date:
                query = """
                    SELECT * FROM stock_dividend_data 
                    WHERE stock_id = %s AND date BETWEEN %s AND %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id, start_date, end_date))
            elif stock_id:
                query = """
                    SELECT * FROM stock_dividend_data 
                    WHERE stock_id = %s 
                    ORDER BY date DESC
                """
                cursor.execute(query, (stock_id,))
            elif start_date and end_date:
                query = """
                    SELECT * FROM stock_dividend_data 
                    WHERE date BETWEEN %s AND %s 
                     ORDER BY stock_id, date DESC
                """
                cursor.execute(query, (start_date, end_date))
            else:
                query = "SELECT * FROM stock_dividend_data ORDER BY stock_id, date DESC"
                cursor.execute(query)
            
            data = cursor.fetchall()
            cursor.close()
            
            return data
            
        except Exception as e:
            logger.error(f"獲取股利政策數據失敗: {e}")
            return None
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法"""
        return self.run(start_date=start_date, end_date=end_date, stock_list=stock_list, rate_limiter=rate_limiter, use_custom_range=use_custom_range, progress_manager=progress_manager)

    # 保留舊方法名稱以維持向後兼容性
    def collect_dividend_data(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """向後兼容的方法，呼叫新的 run 方法"""
        return self.run(start_date=start_date, end_date=end_date, stock_list=stock_list, rate_limiter=rate_limiter, use_custom_range=use_custom_range, progress_manager=progress_manager)
