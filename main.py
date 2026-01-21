#!/usr/bin/env python3
"""
StockHunter FinMind 主程式
整合所有功能並提供統一的調用介面 (Universal Interface)
支持 CLI 和未來的 WebUI
"""

import sys
import logging
import time
from dotenv import load_dotenv

import core.config as config
from core.controller import DataController
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
        logger.info("✓ 所有依賴已安裝")
        return True
    except ImportError as e:
        logger.error(f"✗ 缺少依賴: {e}")
        logger.info("請運行: pip install -r requirements.txt")
        return False

def check_config():
    """檢查配置是否正確"""
    # 這裡可以透過 Controller 的 config 邏輯來檢查
    # 簡單起見，直接保留基本檢查
    return True

def setup_system(controller):
    """系統初始化設置"""
    try:
        # 這裡可以通過 controller 調用 db_manager 初始化
        # 目前 DataController 初始化時已經初始化了 DB Manager
        
        # 檢查資料表
        # TODO: 將 check_tables_exist 邏輯移入 controller
        # 暫時假設如果 DB 連線正常則視為 OK
        status = controller.get_system_status()
        if not status['db_connected']:
             logger.error("無法連接到數據庫！")
             return False
             
        # 可以添加自動創建表格的邏輯
        # if not controller.check_tables():
        #     controller.create_tables()

        return True
    except Exception as e:
        logger.error(f"系統設置異常: {e}")
        return False

def ui_callback_handler(message, level="info"):
    """
    通用 UI 回調處理器，用於接收 Controller 的事件
    """
    if level == "error":
        print(f"❌ {message}")
    elif level == "success":
        print(f"✅ {message}")
    elif level == "info":
        print(f"ℹ️  {message}")
    else:
        print(message)

def main():
    # 1. 檢查依賴
    if not check_dependencies():
        sys.exit(1)
    
    # 2. 初始化控制器 (Core Logic)
    logger.info("正在初始化系統核心...")
    controller = DataController()
    
    # 3. 初始化 UI (View)
    ui = ConsoleUI(controller)
    
    # 4. 系統檢查與設置
    if not setup_system(controller):
        sys.exit(1)
        
    # 5. 顯示歡迎畫面
    ui.display_welcome_message()
    
    # 6. 主循環
    while True:
        try:
            # 顯示主選單
            ui.show_collector_menu()
            
            # 獲取用戶輸入
            choice = ui.get_user_choice()
            
            # 處理通用選項
            if choice == 'exit':
                ui.display_goodbye_message()
                break
                
            elif isinstance(choice, str) and choice in ['status', 'reset_progress', 'drop_database', 'export_csv']:
                # 特殊功能路由
                ui.handle_special_options(choice)
                
            elif isinstance(choice, list):
                # 執行收集器
                ui.show_time_range_menu()
                use_custom_range = ui.get_time_range_choice()
                
                if use_custom_range is not None:
                    print(f"\n🚀 開始執行 {len(choice)} 個收集任務...")
                    
                    # 委派給 Controller 執行，並傳入回調函數處理即時 UI 顯示
                    # 注意: Generator 需要迭代才能執行
                    for msgs in controller.run_collectors(choice, use_custom_range, ui_callback_handler):
                         if isinstance(msgs, dict) and msgs.get('type') == 'wait':
                             # 處理等待邏輯
                             wait_sec = msgs['seconds']
                             print(f"⏳ {msgs['msg']}")
                             time.sleep(wait_sec)

                    print("\n🎉 所有任務執行完畢！")
            
            # 詢問是否繼續
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
