#!/usr/bin/env python3
"""
StockHunter FinMind 主程式
整合所有功能並提供統一的調用介面
支持斷點續傳功能
"""

import os
import sys
import logging
import time
import inspect
from datetime import datetime, timedelta
from dotenv import load_dotenv
from FinMind.data import DataLoader
from progress_manager import CollectorProgressManager, APIRateLimiter
from cli_interface import (
    show_collector_menu, show_time_range_menu, get_user_choice, get_time_range_choice,
    handle_special_options, display_welcome_message, display_goodbye_message
)

# 載入環境變數
load_dotenv('config.env')

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def  get_collector_date_range(collector_name, use_custom_range=False):
    """獲取指定收集器的數據時間範圍
    
    Args:
        collector_name: 收集器名稱
        use_custom_range: 是否使用自定義時間範圍
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    if use_custom_range:
        start_date = os.getenv('DEFAULT_START_DATE', '2020-01-01')
        end_date = os.getenv('DEFAULT_END_DATE', today)
        return f"{start_date} ~ {end_date} (自定義範圍)"
    else:
        # 獲取各收集器的預設最早時間
        start_env_key = f"{collector_name.upper()}_START_DATE"
        earliest_date = os.getenv(start_env_key, '1990-01-01')
        
        if earliest_date == 'all_time':
            return f"無時間限制 (完整)"
        else:
            return f"{earliest_date} ~ {today} (完整)"

def format_date_range(start_date, end_date, is_custom=False):
    """格式化日期範圍顯示"""
    if is_custom:
        return f"{start_date} ~ {end_date} (自定義範圍)"
    else:
        if start_date == 'all_time':
            return f"無時間限制 (完整)"
        else:
            return f"{start_date} ~ {end_date} (完整)"

def show_data_summary():
    """顯示數據摘要"""
    try:
        from database_setup import DatabaseManager
        
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        if conn is None:
            print("❌ 無法連接數據庫")
            return
        
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("📊 數據庫摘要")
        print("="*80)
        
        # 列出所有表格及其記錄數
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("📝 數據庫中尚無表格")
        else:
            print(f"📋 數據庫中共有 {len(tables)} 個表格:")
            print()
            
            total_records = 0
            for (table_name,) in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    total_records += count
                    print(f"  📊 {table_name:<40} {count:>10,} 筆記錄")
                except Exception as e:
                    print(f"  ❌ {table_name:<40} 查詢失敗: {e}")
            
            print("-" * 80)
            print(f"  💾 總記錄數: {total_records:,} 筆")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"顯示數據摘要失敗: {e}")

def check_dependencies():
    """檢查必要的依賴是否已安裝"""
    try:
        import psycopg2
        import pandas
        from FinMind.data import DataLoader
        logger.info("✓ 所有依賴已安裝")
        return True
    except ImportError as e:
        logger.error(f"✗ 缺少依賴: {e}")
        logger.info("請運行: pip install -r requirements.txt")
        return False

def check_config():
    """檢查配置是否正確"""
    required_configs = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    
    missing_configs = []
    for config in required_configs:
        if not os.getenv(config):
            missing_configs.append(config)
    
    if missing_configs:
        logger.error(f"缺少必要配置: {', '.join(missing_configs)}")
        logger.info("請檢查 config.env 檔案")
        return False
    
    logger.info("✓ 配置檢查通過")
    return True

def check_tables_exist():
    """檢查必要的資料表是否存在"""
    try:
        from database_setup import DatabaseManager
        
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        if not conn:
            logger.error("無法連接到資料庫")
            return False
        
        cursor = conn.cursor()
        
        # 檢查關鍵表格是否存在
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        
        cursor.close()
        db_manager.return_connection(conn)
        
        # 如果表格數量少於預期，認為需要重新創建
        if table_count < 20:  # 我們預期至少有20+個表格
            logger.warning(f"檢測到資料表數量不足 ({table_count} 個)，需要重新創建表格")
            return False
        
        logger.info(f"✓ 資料表檢查通過 (共 {table_count} 個表格)")
        return True
        
    except Exception as e:
        logger.error(f"資料表檢查失敗: {e}")
        return False

def setup_database():
    """設置數據庫"""
    try:
        from database_setup import DatabaseManager
        
        # 先檢查表格是否存在
        if check_tables_exist():
            logger.info("✓ 資料庫表格已存在，跳過創建")
            return True
        
        # 表格不存在或不完整，重新創建
        logger.info("🔄 正在創建資料庫表格...")
        db_manager = DatabaseManager()
        success = db_manager.create_tables()
        
        if success:
            logger.info("✓ 資料庫設置完成")
            return True
        else:
            logger.error("✗ 資料庫設置失敗")
            return False
            
    except Exception as e:
        logger.error(f"資料庫設置異常: {e}")
        return False

def get_collector_mapping():
    """獲取收集器編號到模組名稱的對應關係"""
    return {
        1: 'taiwan_stock_info',
        2: 'taiwan_stock_info_with_warrant', 
        3: 'taiwan_stock_trading_date',
        4: 'taiwan_stock_price',
        5: 'taiwan_stock_per',
        6: 'taiwan_stock_statistics_of_order_book_and_trade',
        7: 'taiwan_various_indicators5_seconds',
        8: 'taiwan_stock_day_trading',
        9: 'taiwan_stock_total_return_index',
        10: 'taiwan_stock_margin_purchase_short_sale',
        11: 'taiwan_stock_total_margin_purchase_short_sale',
        12: 'taiwan_stock_institutional_investors_buy_sell',
        13: 'taiwan_stock_total_institutional_investors',
        14: 'taiwan_stock_shareholding',
        15: 'taiwan_stock_securities_lending',
        16: 'taiwan_stock_margin_short_sale_suspension',
        17: 'taiwan_daily_short_sale_balances',
        18: 'taiwan_securities_trader_info',
        19: 'taiwan_stock_financial_statements',
        20: 'taiwan_stock_balance_sheet',
        21: 'taiwan_stock_cash_flows_statement',
        22: 'taiwan_stock_dividend',
        23: 'taiwan_stock_dividend_result',
        24: 'taiwan_stock_month_revenue',
        25: 'taiwan_stock_capital_reduction_reference_price',
        26: 'taiwan_stock_delisting',
        27: 'taiwan_stock_split_price',
        28: 'taiwan_stock_par_value_change'
    }

def run_collectors(collector_choices, use_custom_range=False):
    """執行選擇的收集器"""
    collector_mapping = get_collector_mapping()
    rate_limiter = APIRateLimiter()
    progress_manager = CollectorProgressManager()
    
    success_count = 0
    total_count = len(collector_choices)
    
    for i, choice in enumerate(collector_choices, 1):
        if choice not in collector_mapping:
            logger.error(f"❌ 無效的收集器編號: {choice}")
            continue
        
        module_name = collector_mapping[choice]
        
        print(f"\n{'='*80}")
        print(f"🎯 執行收集器 {i}/{total_count}: {module_name}")
        print(f"{'='*80}")
        
        try:
            # 動態導入收集器模組
            collector_module = __import__(module_name)
            
            # 檢查 API 調用限制
            if not rate_limiter.can_call():
                next_time = rate_limiter.get_next_available_time()
                wait_seconds = (next_time - datetime.now()).total_seconds()
                
                if wait_seconds > 0:
                    print(f"⏰ API 調用限制，需要等待 {int(wait_seconds/60):02d}:{int(wait_seconds%60):02d}")
                    
                    print("\n選項:")
                    print("1. 等待並繼續執行")
                    print("2. 跳過當前收集器並繼續")
                    print("3. 退出程式")
                    
                    while True:
                        choice = input("請選擇 (1/2/3): ").strip()
                        if choice == '1':
                            while not rate_limiter.can_call():
                                remaining = (rate_limiter.get_next_available_time() - datetime.now()).total_seconds()
                                if remaining > 0:
                                    print(f"\r⏳ 剩餘等待時間: {int(remaining/60):02d}:{int(remaining%60):02d}", end="", flush=True)
                                    time.sleep(30)
                                else:
                                    break
                            print("\n✅ 等待完成，繼續執行...")
                            break
                        elif choice == '2':
                            print("⏭️ 跳過當前收集器")
                            continue
                        elif choice == '3':
                            print("👋 程式已退出")
                            return success_count, total_count
                        else:
                            print("❌ 請輸入 1、2 或 3")
            
            # 執行收集器
            # 根據收集器名稱創建適當的類別實例
            collector_class_name = ''.join(word.capitalize() for word in module_name.split('_')) + 'Collector'
            
            if hasattr(collector_module, collector_class_name):
                # 創建收集器實例
                collector_class = getattr(collector_module, collector_class_name)
                collector_instance = collector_class()
                
                # 執行收集器的 main 方法，傳遞所有必要參數
                collector_instance.main(
                    use_custom_range=use_custom_range, 
                    rate_limiter=rate_limiter,
                    progress_manager=progress_manager
                )
                success_count += 1
                print(f"✅ {module_name} 執行完成")
            else:
                logger.error(f"❌ {module_name} 模組缺少 {collector_class_name} 類別")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ {module_name}收集失敗: {error_msg}")
            
            # 檢測是否是 API 限制錯誤
            if rate_limiter.detect_api_limit_error(error_msg):
                choice = rate_limiter.handle_api_limit_error(module_name)
                
                if choice == '1':  # 等待並繼續
                    print(f"⏰ 等待 API 限制解除...")
                    while not rate_limiter.can_call():
                        remaining = (rate_limiter.get_next_available_time() - datetime.now()).total_seconds()
                        if remaining > 0:
                            print(f"\r⏳ 剩餘等待時間: {int(remaining/60):02d}:{int(remaining%60):02d}", end="", flush=True)
                            time.sleep(int(os.getenv('API_WAIT_CHECK_INTERVAL', 30)))
                        else:
                            break
                    print("\n✅ 等待完成，重試當前收集器...")
                    
                    # 重試當前收集器
                    try:
                        collector_class_name = ''.join(word.capitalize() for word in module_name.split('_')) + 'Collector'
                        if hasattr(collector_module, collector_class_name):
                            collector_class = getattr(collector_module, collector_class_name)
                            collector_instance = collector_class()
                            collector_instance.main(use_custom_range=use_custom_range, rate_limiter=rate_limiter)
                            success_count += 1
                            print(f"✅ {module_name} 重試成功")
                        else:
                            logger.error(f"❌ {module_name} 重試失敗: 找不到 {collector_class_name} 類別")
                    except Exception as retry_e:
                        logger.error(f"❌ {module_name} 重試失敗: {retry_e}")
                        
                elif choice == '2':  # 退出程式
                    print("👋 程式已退出")
                    return success_count, total_count
                elif choice == '3':  # 跳過當前收集器
                    print(f"⏭️ 跳過收集器 {module_name}")
                    continue
    
    return success_count, total_count

if __name__ == "__main__":
    # 檢查依賴
    if not check_dependencies():
        logger.warning("請先安裝必要依賴")
        logger.info("運行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 檢查配置
    if not check_config():
        logger.warning("請先配置數據庫連接資訊")
        logger.info("然後重新運行此腳本")
        sys.exit(1)
    
    # 設置數據庫
    if not setup_database():
        logger.error("數據庫設置失敗，請檢查配置")
        sys.exit(1)
    
    # 顯示歡迎訊息
    display_welcome_message()
    
    # 主循環
    while True:
        show_collector_menu()
        choice = get_user_choice()
        
        if choice == 'exit':
            display_goodbye_message()
            break
        elif handle_special_options(choice):
            # 特殊選項已在 handle_special_options 中處理
            pass
        elif isinstance(choice, list):
            # 對於執行收集器的選項，先詢問時間範圍
            show_time_range_menu()
            use_custom_range = get_time_range_choice()
            
            if use_custom_range is None:
                continue  # 用戶取消，回到主選單
            
            print(f"🎯 執行選定的 {len(choice)} 個收集器...")
            success_count, total_stocks = run_collectors(choice, use_custom_range=use_custom_range)
            if success_count == total_stocks:
                print("🎉 選定的數據收集完成！")
            else:
                print(f"⚠️ {total_stocks - success_count} 個收集器執行失敗")
        
        # 詢問是否繼續
        continue_choice = input("\n是否要繼續使用？(y/n): ").strip().lower()
        if continue_choice in ['n', 'no']:
            display_goodbye_message()
            break
