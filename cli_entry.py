import sys
import logging
import time
import argparse
from dotenv import load_dotenv

import core.config as config
from core.collector_engine import CollectorEngine
from ui.cli import ConsoleUI

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """檢查必要的依賴是否已安裝"""
    try:
        import psycopg2
        import pandas
        from FinMind.data import DataLoader
        return True
    except ImportError as e:
        logger.error(f"✗ 缺少依賴: {e}")
        logger.info("請運行: pip install -r requirements.txt")
        return False

def ui_callback_handler(message, level="info"):
    """通用 UI 回調處理器"""
    if level == "error":
        print(f"❌ {message}")
    elif level == "success":
        print(f"✅ {message}")
    elif level == "info":
        print(f"ℹ️  {message}")
    else:
        print(message)

def run_headless(controller, ids_str, start=None, end=None, custom=False):
    """無介面直接執行模式"""
    # 解析 ID
    collector_ids = []
    if ids_str.lower() == 'all':
        collector_ids = list(range(1, 29))
    elif ids_str.lower() in ['technical', 'chip', 'fundamental']:
        groups = controller.get_available_collectors()
        collector_ids = [item['id'] for item in groups.get(ids_str.lower(), [])]
    else:
        collector_ids = [int(x.strip()) for x in ids_str.split(',') if x.strip().isdigit()]

    if not collector_ids:
        print("❌ 未能識別有效的收集器 ID")
        sys.exit(1)

    print(f"🚀 [Headless] 開始執行 {len(collector_ids)} 個收集任務...")
    try:
        for msgs in controller.run_collectors(collector_ids, custom, start, end):
            if isinstance(msgs, dict):
                m_type = msgs.get('type')
                m_msg = msgs.get('msg', '')
                if m_type == 'log':
                    ui_callback_handler(m_msg, msgs.get('level', 'info'))
                elif m_type == 'summary':
                    ui_callback_handler(m_msg, 'success')
    except Exception as e:
        from services.finmind_gateway import RateLimitException
        if isinstance(e, RateLimitException):
            print(f"\n🛑 [Rate Limit Error] 達到 API 頻率限制，中斷任務以供更換 IP: {e}")
            sys.exit(42)
        else:
            print(f"\n❌ [Error] 執行過程中出錯: {e}")
            sys.exit(1)

def main():
    # 0. 參數解析
    parser = argparse.ArgumentParser(description="StockHunter CLI Mode")
    parser.add_argument("--ids", type=str, help="指定收集器 ID (例如: 1,4,10 或 'all' 或 'chip')")
    parser.add_argument("--start", type=str, help="自定義開始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="自定義結束日期 (YYYY-MM-DD)")
    parser.add_argument("--custom", action="store_true", help="強制使用自定義時間範圍模式")
    args = parser.parse_args()

    # 1. 檢查依賴
    if not check_dependencies():
        sys.exit(1)
    
    # 2. 初始化引擎
    controller = CollectorEngine()
    
    # 3. 如果有參數，進入無介面模式
    if args.ids:
        run_headless(controller, args.ids, args.start, args.end, args.custom)
        return

    # 4. 初始化 TUI (互動模式)
    ui = ConsoleUI(controller)
    ui.display_welcome_message()
    
    # 5. 主循環
    while True:
        try:
            ui.show_collector_menu()
            choice = ui.get_user_choice()
            
            if choice == 'exit':
                ui.display_goodbye_message()
                break
            elif isinstance(choice, str):
                ui.handle_special_options(choice)
            elif isinstance(choice, list):
                ui.show_time_range_menu()
                use_custom_range = ui.get_time_range_choice()
                
                if use_custom_range is not None:
                    print(f"\n🚀 開始執行 {len(choice)} 個收集任務...")
                    try:
                        for msgs in controller.run_collectors(choice, use_custom_range):
                             if isinstance(msgs, dict):
                                 m_type = msgs.get('type')
                                 m_msg = msgs.get('msg', '')
                                 if m_type == 'log':
                                     ui_callback_handler(m_msg, msgs.get('level', 'info'))
                                 elif m_type == 'summary':
                                     ui_callback_handler(m_msg, 'success')
                    except Exception as e:
                        from services.finmind_gateway import RateLimitException
                        if isinstance(e, RateLimitException):
                            print(f"\n🛑 [Rate Limit Error] 達到 API 頻率限制: {e}")
                        else:
                            print(f"\n❌ [Error] 執行過程中出錯: {e}")

                    print("\n🎉 所有任務執行完畢！")
            
            continue_choice = input("\n是否要繼續使用？(y/n): ").strip().lower()
            if continue_choice in ['n', 'no']:
                ui.display_goodbye_message()
                break
                
        except KeyboardInterrupt:
            print("\n👋 使用者中斷")
            break
        except Exception as e:
            logger.error(f"未預期的錯誤: {e}")
            input("按 Enter 繼續...")

if __name__ == "__main__":
    main()
