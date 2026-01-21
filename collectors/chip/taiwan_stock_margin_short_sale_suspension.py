#!/usr/bin/env python3
"""
暫停融券賣出數據收集器 / Taiwan Stock Margin Short Sale Suspension Data Collector
專門負責收集台灣個股暫停融券賣出數據 / Specialized in collecting margin short sale suspension data of Taiwan stocks
API: TaiwanStockMarginShortSaleSuspension
"""

import logging
from datetime import datetime
from collectors.base import BaseStockListCollector
import os

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockMarginShortSaleSuspensionCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_margin_short_sale_suspension")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """調用 FinMind API 獲取暫停融券賣出數據"""
        return self.api.get_data(
            dataset='TaiwanStockMarginShortSaleSuspension',
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _save_data(self, df, stock_id) -> bool:
        """儲存暫停融券賣出數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無暫停融券賣出數據，跳過儲存")
            return True
        
        stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_margin_short_sale_suspension_data (
                stock_id, date, end_date, created_at
            )
            VALUES %s
            ON CONFLICT (stock_id, date) 
            DO UPDATE SET 
                end_date = EXCLUDED.end_date,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            # 處理 SuspensionDate (end_date)，將空字符串轉換為 None
            suspension_date = row.get('SuspensionDate')
            if suspension_date == '' or suspension_date is None:
                suspension_date = None
            
            data_rows.append((
                stock_id_val,
                row.get('date'),
                suspension_date,
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆暫停融券賣出數據")
            return True
        else:
            logger.error(f"儲存股票 {stock_id_val} 暫停融券賣出數據失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取暫停融券賣出數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                return None
            try:
                cursor = conn.cursor()
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_margin_short_sale_suspension_data 
                        WHERE stock_id = %s AND date BETWEEN %s AND %s 
                        ORDER BY date
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_margin_short_sale_suspension_data 
                        WHERE stock_id = %s 
                        ORDER BY date
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_margin_short_sale_suspension_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY stock_id, date
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_margin_short_sale_suspension_data ORDER BY stock_id, date"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取暫停融券賣出數據失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主函數，調用父類別的 run 方法"""
        return self.run(start_date, end_date, stock_list, rate_limiter, use_custom_range, progress_manager)


def main():
    """主函數，執行暫停融券賣出資料收集"""
    collector = TaiwanStockMarginShortSaleSuspensionCollector()
    
    # 使用預設環境變數設定
    start_date = os.getenv('TAIWAN_STOCK_MARGIN_SHORT_SALE_SUSPENSION_START_DATE', '2001-01-01')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    total_processed, total_success = collector.run(
        start_date=start_date,
        end_date=end_date,
        use_custom_range=False
    )
    
    print(f"✅ 暫停融券賣出資料收集完成！")
    print(f"📊 處理股票數量: {total_processed}")
    print(f"✅ 成功股票數量: {total_success}")
    print(f"❌ 失敗股票數量: {total_processed - total_success}")
