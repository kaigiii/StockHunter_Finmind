#!/usr/bin/env python3
"""
現金流量表數據收集器 / Taiwan Stock Cash Flows Statement Data Collector
專門負責收集台灣股票的現金流量表資訊 / Specialized in collecting cash flows statement data of Taiwan stocks
API: TaiwanStockCashFlowsStatement
"""

import logging
from datetime import datetime
from collectors.base import BaseStockListCollector

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaiwanStockCashFlowsStatementCollector(BaseStockListCollector):
    def __init__(self):
        super().__init__(collector_name="taiwan_stock_cash_flows_statement")
    
    def _call_api(self, stock_id: str, start_date: str, end_date: str):
        """呼叫 FinMind API 獲取現金流量表數據"""
        return self.api.taiwan_stock_cash_flows_statement(
            stock_id=stock_id,
            start_date=start_date,
        )

    def _save_data(self, df, stock_id) -> bool:
        """儲存現金流量表數據到數據庫 - 使用批次插入優化性能"""
        # 處理空 DataFrame
        if df.empty:
            logger.info(f"股票 {stock_id} 無現金流量表數據，跳過儲存")
            return True
        
        stock_id_val = df['stock_id'].iloc[0] if 'stock_id' in df.columns else stock_id
        
        # 準備批次插入語句
        insert_query = """
            INSERT INTO stock_cash_flows_statement_data (date, stock_id, type, value, origin_name, created_at)
            VALUES %s
            ON CONFLICT (date, stock_id, type) 
            DO UPDATE SET 
                value = EXCLUDED.value,
                origin_name = EXCLUDED.origin_name,
                updated_at = CURRENT_TIMESTAMP
        """
        
        # 準備批次數據
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append((
                row['date'],
                stock_id_val,
                row['type'],
                row['value'],
                row.get('origin_name', ''),
                datetime.now()
            ))
        
        # 執行批次插入
        if self.db_manager.execute_batch(insert_query, data_rows):
            logger.info(f"股票 {stock_id_val} 批次儲存 {len(data_rows)} 筆現金流量表數據")
            return True
        else:
            logger.error(f"儲存股票 {stock_id_val} 現金流量表數據失敗")
            return False

    def get_data(self, stock_id=None, start_date=None, end_date=None):
        """從數據庫獲取現金流量表數據"""
        with self.db_manager.get_db_context() as conn:
            if not conn:
                logger.error("無法獲取資料庫連線")
                return None
            
            try:
                cursor = conn.cursor()
                
                if stock_id and start_date and end_date:
                    query = """
                        SELECT * FROM stock_cash_flows_statement_data 
                        WHERE stock_id = %s AND date BETWEEN %s AND %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id, start_date, end_date))
                elif stock_id:
                    query = """
                        SELECT * FROM stock_cash_flows_statement_data 
                        WHERE stock_id = %s 
                        ORDER BY date DESC
                    """
                    cursor.execute(query, (stock_id,))
                elif start_date and end_date:
                    query = """
                        SELECT * FROM stock_cash_flows_statement_data 
                        WHERE date BETWEEN %s AND %s 
                        ORDER BY stock_id, date DESC
                    """
                    cursor.execute(query, (start_date, end_date))
                else:
                    query = "SELECT * FROM stock_cash_flows_statement_data ORDER BY stock_id, date DESC"
                    cursor.execute(query)
                
                data = cursor.fetchall()
                cursor.close()
                return data
            except Exception as e:
                logger.error(f"獲取現金流量表數據失敗: {e}")
                return None

    def main(self, start_date=None, end_date=None, stock_list=None, rate_limiter=None, use_custom_range=False, progress_manager=None):
        """主要執行方法"""
        return self.run(start_date=start_date, end_date=end_date, stock_list=stock_list, rate_limiter=rate_limiter, use_custom_range=use_custom_range, progress_manager=progress_manager)
