#!/usr/bin/env python3
"""
個股融資融劵表數據收集器 / Taiwan Stock Margin Purchase Short Sale Data Collector
專門負責收集台灣個股融資融券數據 / Specialized in collecting margin purchase and short sale data of Taiwan stocks
API: TaiwanStockMarginPurchaseShortSale
"""

import logging
from datetime import datetime
from collectors.base import BaseStockListCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockMarginPurchaseShortSaleCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_margin_purchase_short_sale")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """調用 FinMind API 獲取個股融資融券數據"""
        return self.api.taiwan_stock_margin_purchase_short_sale(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存個股融資融券數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無融資融券數據，跳過儲存")
            return True
        
        stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_margin_purchase_short_sale_data (
                date, stock_id, marginpurchasetoday, marginsaletoday,
                offsettodaymarginpurchase, offsettodaymarginsale, marginpurchaseyesterday,
                marginsaleyesterday, shortsaletoday, shortcoveringtoday,
                offsettodayshortsale, offsettodayshortcovering, shortsaleyesterday,
                shortcoveringyesterday, quota, note
            )
            VALUES %s
            ON CONFLICT (stock_id, date) 
            DO UPDATE SET 
                marginpurchasetoday = EXCLUDED.marginpurchasetoday,
                marginsaletoday = EXCLUDED.marginsaletoday,
                offsettodaymarginpurchase = EXCLUDED.offsettodaymarginpurchase,
                offsettodaymarginsale = EXCLUDED.offsettodaymarginsale,
                marginpurchaseyesterday = EXCLUDED.marginpurchaseyesterday,
                marginsaleyesterday = EXCLUDED.marginsaleyesterday,
                shortsaletoday = EXCLUDED.shortsaletoday,
                shortcoveringtoday = EXCLUDED.shortcoveringtoday,
                offsettodayshortsale = EXCLUDED.offsettodayshortsale,
                offsettodayshortcovering = EXCLUDED.offsettodayshortcovering,
                shortsaleyesterday = EXCLUDED.shortsaleyesterday,
                shortcoveringyesterday = EXCLUDED.shortcoveringyesterday,
                quota = EXCLUDED.quota,
                note = EXCLUDED.note,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                row.get('date'),
                stock_id_val,
                row.get('MarginPurchaseBuy', 0),
                row.get('MarginPurchaseSell', 0),
                row.get('MarginPurchaseCashRepayment', 0),
                row.get('OffsetLoanAndShort', 0),
                row.get('MarginPurchaseYesterdayBalance', 0),
                row.get('MarginPurchaseTodayBalance', 0),
                row.get('ShortSaleSell', 0),
                row.get('ShortSaleBuy', 0),
                row.get('ShortSaleCashRepayment', 0),
                0,  # offsettodayshortcovering
                row.get('ShortSaleYesterdayBalance', 0),
                row.get('ShortSaleTodayBalance', 0),
                row.get('MarginPurchaseLimit', 0),
                row.get('Note', '')
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆融資融券數據")
            return True
        else:
            logger.error(f"儲存股票 {stock_id_val} 融資融券數據失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取個股融資融券數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            
            try:
                cursor = conn.cursor()
                
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_margin_purchase_short_sale_data 
                        WHERE stock_id = %s AND date BETWEEN %s AND %s 
                        ORDER BY date
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_margin_purchase_short_sale_data 
                        WHERE stock_id = %s 
                        ORDER BY date
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_margin_purchase_short_sale_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY stock_id, date
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_margin_purchase_short_sale_data ORDER BY stock_id, date"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取個股融資融券數據失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)


def main():
    """主函數，執行個股融資融券資料收集"""
    collector = TaiwanStockMarginPurchaseShortSaleCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_MARGIN_PURCHASE_SHORT_SALE_START_DATE', '2001-01-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    total_processed, total_success = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    print(f"✅ 個股融資融券資料收集完成！")
    print(f"📊 處理股票數量: {total_processed}")
    print(f"✅ 成功股票數量: {total_success}")
    print(f"❌ 失敗股票數量: {total_processed - total_success}")
