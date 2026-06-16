import importlib
import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv

import core.config as config
from core.database import DatabaseManager
from services.data_exporter import DataExporter
from services.api_throttler import APIThrottler
from utils.checkpoint_manager import CheckpointManager

load_dotenv('.env')
logger = logging.getLogger(__name__)

class CollectorEngine:
    """
    通用數據收集引擎
    負責協調數據收集、匯出、資料庫管理等核心業務邏輯
    與具體的使用者介面（CLI/Web）解耦
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.rate_limiter = APIThrottler()
        self.checkpoint_manager = CheckpointManager()
        self.exporter = DataExporter(self.db_manager)
        
    def get_system_status(self):
        """獲取系統狀態摘要"""
        token_count = len(config.FINMIND_API_TOKENS)
        conn = self.db_manager.get_connection()
        db_connected = conn is not None
        if db_connected:
            self.db_manager.return_connection(conn)
            
        return {
            "token_count": token_count,
            "token_mode": "Revolver" if token_count > 1 else ("Single" if token_count == 1 else "Anonymous"),
            "db_connected": db_connected,
            "rate_limiter_status": {
                "max_calls": self.rate_limiter.max_calls_per_hour,
                "can_call": self.rate_limiter.can_call()
            }
        }

    def get_available_collectors(self):
        """獲取所有可用的收集器及其詳細狀態"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        groups = {
            "technical": [
                {"id": 1, "name": "台股總覽", "range": "無時間限制 (完整)"},
                {"id": 2, "name": "台股總覽(含權證)", "range": "無時間限制 (完整)"},
                {"id": 3, "name": "台股交易日", "range": "無時間限制 (完整)"},
                {"id": 4, "name": "股價日成交資訊", "range": f"1994-10-01 ~ {today} (完整)"},
                {"id": 5, "name": "個股PER、PBR資料表", "range": f"2005-10-01 ~ {today} (完整)"},
                {"id": 6, "name": "每5秒委託成交統計", "range": f"2005-01-01 ~ {today} (完整)"},
                {"id": 7, "name": "加權指數", "range": f"2020-01-01 ~ {today} (完整)"},
                {"id": 8, "name": "當日沖銷交易標的及成交量值", "range": f"2014-01-01 ~ {today} (完整)"},
                {"id": 9, "name": "加權、櫃買報酬指數", "range": f"2003-01-01 ~ {today} (完整)"}
            ],
            "chip": [
                {"id": 10, "name": "個股融資融劵表", "range": f"2001-01-01 ~ {today} (完整)"},
                {"id": 11, "name": "台灣市場整體融資融劵表", "range": f"2001-01-01 ~ {today} (完整)"},
                {"id": 12, "name": "法人買賣表", "range": f"2005-01-01 ~ {today} (完整)"},
                {"id": 13, "name": "台灣市場整體法人買賣表", "range": f"2004-04-01 ~ {today} (完整)"},
                {"id": 14, "name": "外資持股表", "range": f"2004-02-01 ~ {today} (完整)"},
                {"id": 15, "name": "借券成交明細", "range": f"2001-05-01 ~ {today} (完整)"},
                {"id": 16, "name": "暫停融券賣出表(融券回補日)", "range": f"2015-01-01 ~ {today} (完整)"},
                {"id": 17, "name": "信用額度總量管制餘額表", "range": f"2005-07-01 ~ {today} (完整)"},
                {"id": 18, "name": "證券商資訊表", "range": "無時間限制 (完整)"}
            ],
            "fundamental": [
                {"id": 19, "name": "綜合損益表", "range": f"1990-03-01 ~ {today} (完整)"},
                {"id": 20, "name": "資產負債表", "range": f"2011-12-01 ~ {today} (完整)"},
                {"id": 21, "name": "現金流量表", "range": f"2008-06-01 ~ {today} (完整)"},
                {"id": 22, "name": "股利政策表", "range": f"2005-05-01 ~ {today} (完整)"},
                {"id": 23, "name": "除權除息結果表", "range": f"2003-05-01 ~ {today} (完整)"},
                {"id": 24, "name": "月營收表", "range": f"2002-02-01 ~ {today} (完整)"},
                {"id": 25, "name": "減資恢復買賣參考價格", "range": f"2011-01-01 ~ {today} (完整)"},
                {"id": 26, "name": "台灣股票下市櫃表", "range": f"2001-01-01 ~ {today} (完整)"},
                {"id": 27, "name": "台股分割後參考價", "range": "無時間限制 (完整)"},
                {"id": 28, "name": "台股變更面額恢復買賣參考價格", "range": f"2020-01-01 ~ {today} (完整)"}
            ]
        }

        # 獲取所有收集器的狀態摘要
        status_map = self.checkpoint_manager.get_all_collectors_status()
        collector_mapping = self._get_collector_mapping()
        
        for g in groups:
            for item in groups[g]:
                module_path = collector_mapping.get(item['id'])
                if module_path:
                    name = module_path.split('.')[-1]
                    item_status = status_map.get(name, {"count": 0, "last_update": "從未執行"})
                    item['last_update'] = item_status['last_update']
                    item['completed_count'] = item_status['count']
        
        return groups

    def _get_collector_mapping(self):
        """內部方法: 獲取編號到模組的映射"""
        return {
            1: 'collectors.technical.taiwan_stock_info',
            2: 'collectors.technical.taiwan_stock_info_with_warrant', 
            3: 'collectors.technical.taiwan_stock_trading_date',
            4: 'collectors.technical.taiwan_stock_price',
            5: 'collectors.technical.taiwan_stock_per',
            6: 'collectors.technical.taiwan_stock_statistics_of_order_book_and_trade',
            7: 'collectors.technical.taiwan_various_indicators5_seconds',
            8: 'collectors.technical.taiwan_stock_day_trading',
            9: 'collectors.technical.taiwan_stock_total_return_index',
            10: 'collectors.chip.taiwan_stock_margin_purchase_short_sale',
            11: 'collectors.chip.taiwan_stock_total_margin_purchase_short_sale',
            12: 'collectors.chip.taiwan_stock_institutional_investors_buy_sell',
            13: 'collectors.chip.taiwan_stock_total_institutional_investors',
            14: 'collectors.chip.taiwan_stock_shareholding',
            15: 'collectors.chip.taiwan_stock_securities_lending',
            16: 'collectors.chip.taiwan_stock_margin_short_sale_suspension',
            17: 'collectors.chip.taiwan_daily_short_sale_balances',
            18: 'collectors.chip.taiwan_securities_trader_info',
            19: 'collectors.fundamental.taiwan_stock_financial_statements',
            20: 'collectors.fundamental.taiwan_stock_balance_sheet',
            21: 'collectors.fundamental.taiwan_stock_cash_flows_statement',
            22: 'collectors.fundamental.taiwan_stock_dividend',
            23: 'collectors.fundamental.taiwan_stock_dividend_result',
            24: 'collectors.fundamental.taiwan_stock_month_revenue',
            25: 'collectors.fundamental.taiwan_stock_capital_reduction_reference_price',
            26: 'collectors.fundamental.taiwan_stock_delisting',
            27: 'collectors.fundamental.taiwan_stock_split_price',
            28: 'collectors.fundamental.taiwan_stock_par_value_change'
        }

    def run_collectors(self, collector_ids, use_custom_range=False, start_date=None, end_date=None):
        """
        執行多個收集器任務 (Generator 模式)
        Yields:
            dict: 包含 type, msg, level 等資訊的消息
        """
        collector_mapping = self._get_collector_mapping()
        success_count = 0
        total_count = len(collector_ids)
        
        for i, choice in enumerate(collector_ids, 1):
            if choice not in collector_mapping:
                msg = f"無效的收集器編號: {choice}"
                yield {"type": "log", "msg": msg, "level": "error"}
                continue
            
            full_module_name = collector_mapping[choice]
            module_basename = full_module_name.split('.')[-1]
            
            try:
                # 1. 檢查 API 限制 (修復：找回被刪除的檢查邏輯)
                if not self.rate_limiter.can_call():
                    if config.API_RATE_LIMIT_ACTION == 'stop':
                        from services.finmind_gateway import RateLimitException
                        raise RateLimitException("API 調用次數已達設定上限。")
                    
                    next_time = self.rate_limiter.get_next_available_time()
                    wait_seconds = (next_time - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        wait_msg = f"API 頻率限制中，需等待 {int(wait_seconds)} 秒..."
                        yield {"type": "log", "msg": wait_msg, "level": "info"}
                        yield {"type": "wait", "seconds": wait_seconds, "msg": wait_msg}
                        # 在控制器層進行實際等待，確保安全
                        time.sleep(wait_seconds + 1)

                # 2. 動態導入與實例化
                module = importlib.import_module(full_module_name)
                class_name = "".join(word.capitalize() for word in module_basename.split("_")) + "Collector"
                
                if not hasattr(module, class_name):
                    yield {"type": "log", "msg": f"找不到類別 {class_name}", "level": "error"}
                    continue
                    
                collector_class = getattr(module, class_name)
                collector_instance = collector_class()
                
                collector_name = getattr(collector_instance, 'collector_name', module_basename)
                yield {"type": "log", "msg": f"[{i}/{total_count}] 正在啟動: {collector_name}", "level": "info"}
                
                # 3. 執行收集
                # 注意：這裡我們假設 collector.main 是同步執行的
                collector_instance.main(
                    start_date=start_date,
                    end_date=end_date,
                    use_custom_range=use_custom_range,
                    rate_limiter=self.rate_limiter,
                    progress_manager=self.checkpoint_manager
                )
                
                success_count += 1
                yield {"type": "log", "msg": f"✅ {collector_name} 執行完成", "level": "success"}
                
            except Exception as e:
                from services.finmind_gateway import RateLimitException
                if isinstance(e, RateLimitException):
                    error_msg = f"🛑 觸發 API 上限停止機制: {str(e)}"
                    logger.error(error_msg)
                    yield {"type": "log", "msg": error_msg, "level": "error"}
                    raise e
                
                error_msg = f"❌ {module_basename} 發生錯誤: {str(e)}"
                logger.error(error_msg)
                yield {"type": "log", "msg": error_msg, "level": "error"}
        
        final_msg = f"任務結束: 成功 {success_count} / 總數 {total_count}"
        yield {"type": "summary", "msg": final_msg, "success": success_count, "total": total_count}

    def reset_progress(self, collector_name=None):
        """重置進度"""
        if collector_name:
            self.checkpoint_manager.reset_collector(collector_name)
        else:
            self.checkpoint_manager.reset_all_progress()

    def drop_all_tables(self):
        """刪除並重建所有表格"""
        if self.db_manager.drop_all_tables():
            return self.db_manager.create_tables()
        return False
        
    def get_export_tables(self):
        """獲取可匯出的表格資訊"""
        tables = self.exporter.get_available_tables()
        result = []
        for table in tables:
            info = self.exporter.get_table_display_info(table)
            info['table_name'] = table
            info['filterable'] = table in self.exporter.FILTERABLE_TABLES
            result.append(info)
        return result
        
    def export_csv(self, table_name, output_filename, stock_ids=None):
        """匯出 CSV"""
        return self.exporter.export_to_csv(table_name, output_filename, stock_ids)
