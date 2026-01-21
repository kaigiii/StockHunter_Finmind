#!/usr/bin/env python3
"""
數據匯出器 / Data Exporter
專門負責將數據庫中的股票數據匯出為 CSV 檔案 / Specialized in exporting stock data from database to CSV files
"""

import logging
import pandas as pd
import os
from datetime import datetime
from core.database import DatabaseManager

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExporter:
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化數據匯出器
        
        Args:
            db_manager (DatabaseManager): 資料庫管理器實例
        """
        self.db_manager = db_manager
        
        # 設置匯出資料夾
        self.export_dir = "csv_exports"
        
        # 確保匯出資料夾存在
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
            logger.info(f"✅ 創建匯出資料夾: {self.export_dir}")
        
        # 定義表格名稱對應的中文名稱和順序
        self.TABLE_INFO = {
            'stock_info_data': {
                'order': 1,
                'chinese_name': '台股總覽',
                'api_name': 'TaiwanStockInfo'
            },
            'stock_info_with_warrant_data': {
                'order': 2, 
                'chinese_name': '台股總覽(含權證)',
                'api_name': 'TaiwanStockInfoWithWarrant'
            },
            'stock_trading_date_data': {
                'order': 3,
                'chinese_name': '台股交易日',
                'api_name': 'TaiwanStockTradingDate'
            },
            'stock_price_data': {
                'order': 4,
                'chinese_name': '股價日成交資訊',
                'api_name': 'TaiwanStockPrice'
            },
            'stock_per_data': {
                'order': 5,
                'chinese_name': '個股PER、PBR資料表',
                'api_name': 'TaiwanStockPER'
            },
            'stock_statistics_of_order_book_and_trade_data': {
                'order': 6,
                'chinese_name': '每5秒委託成交統計',
                'api_name': 'TaiwanStockStatisticsOfOrderBookAndTrade'
            },
            'various_indicators5_seconds_data': {
                'order': 7,
                'chinese_name': '加權指數',
                'api_name': 'TaiwanVariousIndicators5Seconds'
            },
            'stock_day_trading_data': {
                'order': 8,
                'chinese_name': '當日沖銷交易標的及成交量值',
                'api_name': 'TaiwanStockDayTrading'
            },
            'stock_total_return_index_data': {
                'order': 9,
                'chinese_name': '加權、櫃買報酬指數',
                'api_name': 'TaiwanStockTotalReturnIndex'
            },
            'stock_margin_purchase_short_sale_data': {
                'order': 10,
                'chinese_name': '個股融資融劵表',
                'api_name': 'TaiwanStockMarginPurchaseShortSale'
            },
            'stock_total_margin_purchase_short_sale_data': {
                'order': 11,
                'chinese_name': '台灣市場整體融資融劵表',
                'api_name': 'TaiwanStockTotalMarginPurchaseShortSale'
            },
            'stock_institutional_investors_buy_sell_data': {
                'order': 12,
                'chinese_name': '法人買賣表',
                'api_name': 'TaiwanStockInstitutionalInvestorsBuySell'
            },
            'stock_total_institutional_investors_data': {
                'order': 13,
                'chinese_name': '台灣市場整體法人買賣表',
                'api_name': 'TaiwanStockTotalInstitutionalInvestors'
            },
            'stock_shareholding_data': {
                'order': 14,
                'chinese_name': '外資持股表',
                'api_name': 'TaiwanStockShareholding'
            },
            'stock_securities_lending_data': {
                'order': 15,
                'chinese_name': '借券成交明細',
                'api_name': 'TaiwanStockSecuritiesLending'
            },
            'stock_margin_short_sale_suspension_data': {
                'order': 16,
                'chinese_name': '暫停融券賣出表(融券回補日)',
                'api_name': 'TaiwanStockMarginShortSaleSuspension'
            },
            'daily_short_sale_balances_data': {
                'order': 17,
                'chinese_name': '信用額度總量管制餘額表',
                'api_name': 'TaiwanDailyShortSaleBalances'
            },
            'securities_trader_info_data': {
                'order': 18,
                'chinese_name': '證券商資訊表',
                'api_name': 'TaiwanSecuritiesTraderInfo'
            },
            'stock_financial_statements_data': {
                'order': 19,
                'chinese_name': '綜合損益表',
                'api_name': 'TaiwanStockFinancialStatements'
            },
            'stock_balance_sheet_data': {
                'order': 20,
                'chinese_name': '資產負債表',
                'api_name': 'TaiwanStockBalanceSheet'
            },
            'stock_cash_flows_statement_data': {
                'order': 21,
                'chinese_name': '現金流量表',
                'api_name': 'TaiwanStockCashFlowsStatement'
            },
            'stock_dividend_data': {
                'order': 22,
                'chinese_name': '股利政策表',
                'api_name': 'TaiwanStockDividend'
            },
            'stock_dividend_result_data': {
                'order': 23,
                'chinese_name': '除權除息結果表',
                'api_name': 'TaiwanStockDividendResult'
            },
            'stock_month_revenue_data': {
                'order': 24,
                'chinese_name': '月營收表',
                'api_name': 'TaiwanStockMonthRevenue'
            },
            'stock_capital_reduction_reference_price_data': {
                'order': 25,
                'chinese_name': '減資恢復買賣參考價格',
                'api_name': 'TaiwanStockCapitalReductionReferencePrice'
            },
            'stock_delisting_data': {
                'order': 26,
                'chinese_name': '台灣股票下市櫃表',
                'api_name': 'TaiwanStockDelisting'
            },
            'stock_split_price_data': {
                'order': 27,
                'chinese_name': '台股分割後參考價',
                'api_name': 'TaiwanStockSplitPrice'
            },
            'stock_par_value_change_data': {
                'order': 28,
                'chinese_name': '台灣股票變更面額恢復買賣參考價格',
                'api_name': 'TaiwanStockParValueChange'
            }
        }
        
        # 定義包含 stock_id 欄位、可以被篩選的表格名稱
        self.FILTERABLE_TABLES = [
            'stock_info_data',
            'stock_info_with_warrant_data', 
            'stock_price_data',
            'stock_per_data',
            'stock_day_trading_data',
            'stock_total_return_index_data',
            'stock_margin_purchase_short_sale_data',
            'stock_institutional_investors_buy_sell_data',
            'stock_shareholding_data',
            'stock_securities_lending_data',
            'stock_margin_short_sale_suspension_data',
            'daily_short_sale_balances_data',
            'stock_financial_statements_data',
            'stock_balance_sheet_data',
            'stock_cash_flows_statement_data',
            'stock_dividend_data',
            'stock_dividend_result_data',
            'stock_month_revenue_data',
            'stock_capital_reduction_reference_price_data',
            'stock_delisting_data',
            'stock_split_price_data',
            'stock_par_value_change_data'
        ]

    def get_available_tables(self):
        """
        獲取資料庫中所有可用的表格名稱，按照指定順序和中文名稱返回
        
        Returns:
            list: 包含所有表格名稱的列表，如果出錯則返回空列表
        """
        conn = None
        try:
            # 從連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return []
            
            cursor = conn.cursor()
            
            # 查詢所有表格名稱
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            # 獲取資料庫中實際存在的表格
            existing_tables = set(row[0] for row in cursor.fetchall())
            cursor.close()
            
            # 按照指定順序排列，只包含實際存在的表格
            sorted_tables = []
            for table_name, info in sorted(self.TABLE_INFO.items(), key=lambda x: x[1]['order']):
                if table_name in existing_tables:
                    sorted_tables.append(table_name)
            
            # 添加任何不在 TABLE_INFO 中但存在於資料庫的表格
            for table_name in existing_tables:
                if table_name not in self.TABLE_INFO and table_name not in sorted_tables:
                    sorted_tables.append(table_name)
            
            logger.info(f"獲取到 {len(sorted_tables)} 個可用表格")
            return sorted_tables
            
        except Exception as e:
            logger.error(f"獲取可用表格失敗: {e}")
            return []
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def get_table_display_info(self, table_name: str):
        """
        獲取表格的顯示資訊
        
        Args:
            table_name (str): 表格名稱
            
        Returns:
            dict: 包含中文名稱、API名稱等資訊
        """
        if table_name in self.TABLE_INFO:
            return self.TABLE_INFO[table_name]
        else:
            # 如果不在預定義清單中，返回預設資訊
            return {
                'order': 999,
                'chinese_name': table_name,
                'api_name': table_name
            }

    def export_to_csv(self, table_name: str, output_filename: str, stock_ids: list = None):
        """
        將指定表格的數據匯出為 CSV 檔案
        
        Args:
            table_name (str): 要匯出的表格名稱
            output_filename (str): 輸出的 CSV 檔案名稱
            stock_ids (list, optional): 要篩選的股票代碼列表，預設為 None
            
        Returns:
            bool: 匯出成功返回 True，失敗返回 False
        """
        conn = None
        try:
            # 從連線池獲取連線
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return False
            
            # 構建完整的檔案路徑（包含匯出資料夾）
            full_output_path = os.path.join(self.export_dir, output_filename)
            
            # 構建 SQL 查詢
            base_query = f"SELECT * FROM {table_name}"
            
            # 檢查是否需要篩選股票代碼
            if stock_ids and len(stock_ids) > 0:
                # 檢查該表格是否支援股票代碼篩選
                if table_name in self.FILTERABLE_TABLES:
                    sql_query = base_query + " WHERE stock_id IN %s ORDER BY stock_id, date DESC"
                    logger.info(f"將從表格 {table_name} 匯出 {len(stock_ids)} 支股票的數據")
                    # 使用參數化查詢執行
                    df = pd.read_sql_query(sql_query, conn, params=(tuple(stock_ids),))
                else:
                    logger.warning(f"表格 {table_name} 不支援股票代碼篩選，將匯出全部數據")
                    df = pd.read_sql_query(base_query, conn)
            else:
                # 沒有提供股票代碼篩選，匯出全部數據
                logger.info(f"將匯出表格 {table_name} 的全部數據")
                df = pd.read_sql_query(base_query, conn)
            
            # 處理查詢結果
            if df.empty:
                logger.warning(f"表格 {table_name} 沒有數據可匯出")
                return True  # 沒有數據也算是成功的操作
            
            # 將數據保存為 CSV（保存到匯出資料夾中）
            df.to_csv(full_output_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 成功匯出 {len(df)} 筆數據到 {full_output_path}")
            
            # 顯示匯出統計資訊
            if stock_ids and len(stock_ids) > 0 and table_name in self.FILTERABLE_TABLES:
                unique_stocks = df['stock_id'].nunique() if 'stock_id' in df.columns else 0
                logger.info(f"📊 匯出統計: {unique_stocks} 支股票，共 {len(df)} 筆記錄")
            else:
                logger.info(f"📊 匯出統計: 共 {len(df)} 筆記錄")
            
            return True
            
        except Exception as e:
            logger.error(f"匯出數據失敗: {e}")
            return False
        finally:
            # 確保連線歸還到連線池
            if conn:
                self.db_manager.return_connection(conn)

    def export_multiple_tables(self, tables_config: dict, output_dir: str = "./exports/"):
        """
        批次匯出多個表格
        
        Args:
            tables_config (dict): 表格配置字典，格式為 {table_name: {'stock_ids': [...], 'filename': '...'}}
            output_dir (str): 輸出目錄，預設為 "./exports/"
            
        Returns:
            dict: 包含每個表格匯出結果的字典
        """
        import os
        
        # 確保輸出目錄存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"創建輸出目錄: {output_dir}")
        
        results = {}
        
        for table_name, config in tables_config.items():
            try:
                stock_ids = config.get('stock_ids', None)
                filename = config.get('filename', f"{table_name}.csv")
                output_path = os.path.join(output_dir, filename)
                
                logger.info(f"開始匯出表格: {table_name}")
                success = self.export_to_csv(table_name, output_path, stock_ids)
                results[table_name] = {'success': success, 'output_path': output_path}
                
                if success:
                    logger.info(f"✅ 表格 {table_name} 匯出成功")
                else:
                    logger.error(f"❌ 表格 {table_name} 匯出失敗")
                    
            except Exception as e:
                logger.error(f"處理表格 {table_name} 時發生錯誤: {e}")
                results[table_name] = {'success': False, 'error': str(e)}
        
        # 顯示總結
        successful_exports = sum(1 for result in results.values() if result.get('success', False))
        total_exports = len(tables_config)
        logger.info(f"📊 批次匯出完成: {successful_exports}/{total_exports} 個表格匯出成功")
        
        return results

    def get_table_info(self, table_name: str):
        """
        獲取指定表格的基本資訊
        
        Args:
            table_name (str): 表格名稱
            
        Returns:
            dict: 包含表格資訊的字典，包括欄位名稱、數據筆數等
        """
        conn = None
        try:
            conn = self.db_manager.get_connection()
            if not conn:
                logger.error("無法獲取資料庫連線")
                return None
            
            cursor = conn.cursor()
            
            # 獲取表格欄位資訊
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns_info = cursor.fetchall()
            
            # 獲取表格記錄數
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # 如果表格包含 stock_id，獲取唯一股票數量
            stock_count = None
            if table_name in self.FILTERABLE_TABLES:
                cursor.execute(f"SELECT COUNT(DISTINCT stock_id) FROM {table_name}")
                stock_count = cursor.fetchone()[0]
            
            cursor.close()
            
            table_info = {
                'table_name': table_name,
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns_info],
                'row_count': row_count,
                'stock_count': stock_count,
                'is_filterable': table_name in self.FILTERABLE_TABLES
            }
            
            logger.info(f"獲取表格 {table_name} 資訊成功")
            return table_info
            
        except Exception as e:
            logger.error(f"獲取表格 {table_name} 資訊失敗: {e}")
            return None
        finally:
            if conn:
                self.db_manager.return_connection(conn)


def main():
    """示範如何使用 DataExporter"""
    
    # 初始化資料庫管理器和數據匯出器
    db_manager = DatabaseManager()
    exporter = DataExporter(db_manager)
    
    # 獲取所有可用表格
    tables = exporter.get_available_tables()
    print(f"可用表格: {tables}")
    
    # 示範匯出特定股票的價格數據
    stock_list = ['2330', '2317', '1301']  # 台積電、鴻海、台塑
    
    # 單個表格匯出示例
    success = exporter.export_to_csv(
        table_name='stock_price_data',
        output_filename='selected_stocks_price.csv',
        stock_ids=stock_list
    )
    
    if success:
        print("✅ 數據匯出成功！")
    else:
        print("❌ 數據匯出失敗！")
    
    # 批次匯出示例
    export_config = {
        'stock_price_data': {
            'stock_ids': stock_list,
            'filename': 'batch_price_data.csv'
        },
        'stock_per_data': {
            'stock_ids': stock_list,
            'filename': 'batch_per_data.csv'
        }
    }
    
    batch_results = exporter.export_multiple_tables(export_config)
    print(f"批次匯出結果: {batch_results}")


if __name__ == "__main__":
    main()
