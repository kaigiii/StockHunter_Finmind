#!/usr/bin/env python3
"""
StockHunter FinMind CLI 介面模組
負責處理所有使用者介面相關功能，包括選單顯示、使用者輸入處理等
現在已重構為僅負責 UI，業務邏輯由 core.controller.DataController 處理
"""

import os
import logging
import re
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logger = logging.getLogger(__name__)

class ConsoleUI:
    """控制台使用者介面"""
    
    def __init__(self, controller):
        self.controller = controller

    def get_display_width(self, text):
        """計算字符串的顯示寬度（中文字符計為2，英文字符計為1）"""
        width = 0
        for char in str(text):
            if ord(char) > 127:  # 非ASCII字符（包括中文）
                width += 2
            else:
                width += 1
        return width

    def format_aligned_text(self, text, target_width):
        """格式化文本使其達到目標寬度"""
        current_width = self.get_display_width(text)
        if current_width < target_width:
            return text + ' ' * (target_width - current_width)
        return text

    def show_collector_status(self):
        """顯示所有收集器狀態"""
        try:
            print("\n" + "="*80)
            print("收集器狀態概覽")
            print("="*80)
            
            # 使用 Controller 中的 progress_manager
            self.controller.checkpoint_manager.show_status()
            
        except Exception as e:
            print(f"[Error] 顯示收集器狀態失敗: {e}")
            logger.error(f"顯示收集器狀態失敗: {e}")

    def show_data_summary(self):
        """顯示數據摘要"""
        try:
            print("\n" + "="*80)
            print("數據摘要")
            print("="*80)
            print("此功能尚在開發中...")
            print("未來將顯示:")
            print("  - 各表格記錄數量")
            print("  - 數據更新時間")
            print("  - 數據完整性檢查")
            
        except Exception as e:
            logger.error(f"顯示數據摘要失敗: {e}")

    def drop_all_database_tables(self):
        """刪除所有資料庫表格功能"""
        print("\n" + "="*80)
        print("刪除所有資料庫表格")
        print("="*80)
        
        print("警告: 此操作將刪除所有資料庫表格和其中的數據！")
        print("此操作不可逆轉，所有數據將永久丟失！")
        print("\n請確認您要執行此操作：")
        
        # 第一次確認
        confirm1 = input("輸入 'DELETE' 以確認刪除操作: ").strip()
        if confirm1 != 'DELETE':
            print("操作已取消")
            return
        
        # 第二次確認
        print(f"\n[Confirm] 最後確認: 您確定要刪除所有資料庫表格嗎？")
        confirm2 = input("輸入 'YES' 以最終確認: ").strip()
        if confirm2 != 'YES':
            print("操作已取消")
            return
        
        try:
            print("\n正在刪除所有資料庫表格...")
            
            # 使用 Controller 執行刪除操作
            if self.controller.drop_all_tables():
                # 刪除資料表後重置所有下載進度
                self.controller.reset_progress()
                print("所有下載進度已重置！")
                print("\n所有資料庫表格已成功刪除！")
                print("提示: 您可以重新運行任何收集器來重新創建表格和收集數據")
            else:
                 print("\n刪除資料庫表格失敗")

        except Exception as e:
            print(f"\n刪除資料庫表格時發生錯誤: {e}")
            logger.error(f"刪除資料庫表格失敗: {e}")
        
        input("\n按 Enter 鍵返回主選單...")

    def reset_download_progress(self):
        """重置下載進度功能"""
        print("\n" + "="*80)
        print("重置下載進度")
        print("="*80)
        
        # 先顯示當前狀態
        print("當前進度狀態:")
        self.controller.checkpoint_manager.show_status()
        
        print("\n" + "="*50)
        print("請選擇重置選項:")
        print("1. 重置所有收集器進度")
        print("2. 重置單個收集器進度")
        print("3. 僅查看狀態，不進行重置")
        print("0. 返回主選單")
        
        while True:
            try:
                choice = input("\n請選擇選項 (0-3): ").strip()
                
                if choice == '0':
                    print("返回主選單")
                    return
                    
                elif choice == '1':
                    print("\n警告: 此操作將清除所有收集器的下載進度！")
                    confirm = input("確定要重置所有進度嗎？(y/N): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        self.controller.reset_progress()
                        print("所有進度已重置")
                    else:
                        print("操作已取消")
                    return
                    
                elif choice == '2':
                    print("\n可用的收集器:")
                    # 這裡應該顯示所有收集器列表，但為了簡化，我們讓用戶直接輸入
                    collector_name = input("請輸入收集器名稱 (例如: taiwan_stock_info): ").strip()
                    if collector_name:
                        confirm = input(f"確定要重置 {collector_name} 的進度嗎？(y/N): ").strip().lower()
                        if confirm in ['y', 'yes']:
                             self.controller.reset_progress(collector_name)
                        else:
                            print("操作已取消")
                    return
                    
                elif choice == '3':
                    print("當前狀態已顯示在上方")
                    return
                    
                else:
                    print("請輸入 0-3 之間的數字")
                    
            except KeyboardInterrupt:
                print("\n操作已取消")
                return
            except Exception as e:
                print(f"發生錯誤: {e}")

    def show_collector_menu(self):
        """顯示收集器選單"""
        print("\n" + "="*80)
        print("StockHunter FinMind 數據收集器")
        print("="*80)
        
        # 顯示當前時間範圍設定
        default_start = os.getenv('DEFAULT_START_DATE', '2020-01-01')
        default_end = os.getenv('DEFAULT_END_DATE', '2025-12-31')
        print(f"當前自定義時間範圍: {default_start} ~ {default_end}")
        
        print("請選擇要執行的收集器 (按投資分析面向分類):")
        print()
        
        # 從 Controller 獲取收集器列表
        collectors = self.controller.get_available_collectors()
        
        # 技術面
        print("技術面分析:")
        for collector in collectors.get('technical', []):
            formatted_name = self.format_aligned_text(collector['name'], 30)
            print(f"  {collector['id']:2d}. {formatted_name} [{collector['range']}]")
        print()
        
        # 籌碼面
        print("籌碼面分析:")
        for collector in collectors.get('chip', []):
            formatted_name = self.format_aligned_text(collector['name'], 30)
            print(f"  {collector['id']:2d}. {formatted_name} [{collector['range']}]")
        print()
        
        # 基本面
        print("基本面分析:")
        for collector in collectors.get('fundamental', []):
            formatted_name = self.format_aligned_text(collector['name'], 30)
            print(f"  {collector['id']:2d}. {formatted_name} [{collector['range']}]")
        print()
        
        print("特殊選項:")
        print(f"  {int(os.getenv('STATUS_CHECK_CODE', 99))}. 檢查收集器狀態")
        print(f"  {int(os.getenv('RESET_PROGRESS_CODE', 98))}. 重置下載進度")
        print(f"  {int(os.getenv('DROP_DATABASE_CODE', 97))}. 刪除所有資料庫表格")
        print(f"  96. 匯出數據為 CSV")
        print(f"   {int(os.getenv('EXIT_CODE', 0))}. 退出")
        print()
        print("提示: 為避免API限制，建議單獨執行各收集器而非全部執行")

    def show_time_range_menu(self):
        """顯示時間範圍選擇選單"""
        print("\n" + "="*80)
        print("選擇數據收集時間範圍")
        print("="*80)
        print("請選擇要使用的時間範圍:")
        print()
        print("1. 完整歷史數據 (使用各收集器的最早可用時間到現在)")
        print("   - 優點: 獲得最完整的歷史數據")
        print("   - 缺點: 數據量大，下載時間長，API 調用次數多")
        print()
        print("2. 自定義時間範圍 (使用 .env 中設定的時間範圍)")
        default_start = os.getenv('DEFAULT_START_DATE', '2020-01-01')
        default_end = os.getenv('DEFAULT_END_DATE', '2025-12-31')
        print(f"   - 時間範圍: {default_start} ~ {default_end}")
        print("   - 優點: 數據量適中，下載速度快")
        print("   - 缺點: 可能缺少更早期的歷史數據")

    def get_time_range_choice(self):
        """獲取時間範圍選擇"""
        while True:
            try:
                choice = input("\n請選擇時間範圍 (1/2): ").strip()
                
                if choice == '1':
                    print("已選擇完整歷史數據")
                    return False  # 不使用自定義範圍
                elif choice == '2':
                    print("已選擇自定義時間範圍")
                    return True  # 使用自定義範圍
                else:
                    print("請輸入 1 或 2")
                    
            except KeyboardInterrupt:
                print("\n已取消選擇")
                return None

    def get_user_choice(self):
        """獲取使用者選擇"""
        while True:
            try:
                choice = input("請輸入選項 (可用逗號分隔多個選項，如: 1,2,3): ").strip()
                
                exit_code = int(os.getenv('EXIT_CODE', 0))
                status_check_code = int(os.getenv('STATUS_CHECK_CODE', 99))
                reset_progress_code = int(os.getenv('RESET_PROGRESS_CODE', 98))
                drop_database_code = int(os.getenv('DROP_DATABASE_CODE', 97))
                min_index = int(os.getenv('MIN_COLLECTOR_INDEX', 1))
                max_index = int(os.getenv('MAX_COLLECTOR_INDEX', 28))
                
                if choice == str(exit_code):
                    return 'exit'
                elif choice == str(status_check_code):
                    return 'status'
                elif choice == str(reset_progress_code):
                    return 'reset_progress'
                elif choice == str(drop_database_code):
                    return 'drop_database'
                elif choice == '96':
                    return 'export_csv'
                else:
                    # 解析多個選項
                    choices = [int(x.strip()) for x in choice.split(',') if x.strip().isdigit()]
                    if all(min_index <= c <= max_index for c in choices):
                        return choices
                    else:
                        print(f"請輸入 {min_index}-{max_index} 之間的數字")
            except ValueError:
                print("請輸入有效的數字")
            except KeyboardInterrupt:
                print("\n程式已取消")
                return 'exit'

    def handle_csv_export(self):
        """處理 CSV 匯出功能"""
        print("\n" + "="*80)
        print("數據匯出功能")
        print("="*80)
        
        try:
            # 使用 Controller 獲取可匯出表格
            print("正在獲取可用表格...")
            available_tables = self.controller.get_export_tables()
            
            if not available_tables:
                print("未找到任何可用的表格，請先執行數據收集器收集數據")
                input("\n按 Enter 鍵返回主選單...")
                return
            
            # 顯示所有可用表格
            print(f"\n找到 {len(available_tables)} 個可用表格:")
            print("-" * 80)
            
            for i, info in enumerate(available_tables, 1):
                filter_status = "可篩選" if info['filterable'] else "不可篩選"
                print(f"{i:2d}. {info['chinese_name']} ({info['api_name']})")
                print(f"    表格: {info['table_name']} [{filter_status}]")
            
            print("-" * 80)
            
            # 讓使用者選擇表格
            while True:
                try:
                    choice = input(f"\n請選擇要匯出的表格 (1-{len(available_tables)}) 或 0 返回主選單: ").strip()
                    
                    if choice == '0':
                        print("返回主選單")
                        return
                    
                    table_index = int(choice) - 1
                    if 0 <= table_index < len(available_tables):
                        selected_table_info = available_tables[table_index]
                        break
                    else:
                        print(f"請輸入 0-{len(available_tables)} 之間的數字")
                except ValueError:
                    print("請輸入有效的數字")
                except KeyboardInterrupt:
                    print("\n操作已取消")
                    return
            
            selected_table = selected_table_info['table_name']
            print(f"\n已選擇表格: {selected_table}")
            
            # 檢查表格是否可被篩選
            stock_ids = None
            if selected_table_info['filterable']:
                print(f"\n{selected_table} 支援股票代碼篩選")
                print("請選擇匯出選項:")
                print("1. 匯出全部資料")
                print("2. 按指定股票代碼匯出")
                
                while True:
                    try:
                        export_choice = input("請選擇 (1/2): ").strip()
                        
                        if export_choice == '1':
                            print("將匯出全部資料")
                            stock_ids = None
                            break
                        elif export_choice == '2':
                            print("請輸入股票代碼（可用逗號或空格分隔多個代碼）")
                            print("例如: 2330, 2317 0050 或 2330,2317,0050")
                            
                            stock_input = input("股票代碼: ").strip()
                            if not stock_input:
                                print("請輸入至少一個股票代碼")
                                continue
                            
                            # 解析股票代碼
                            stock_ids = re.split(r'[,\s]+', stock_input)
                            stock_ids = [stock.strip() for stock in stock_ids if stock.strip()]
                            
                            if not stock_ids:
                                print("未能解析到有效的股票代碼")
                                continue
                            
                            print(f"將匯出以下股票的數據: {', '.join(stock_ids)}")
                            break
                        else:
                            print("請輸入 1 或 2")
                    except KeyboardInterrupt:
                        print("\n操作已取消")
                        return
            else:
                print(f"\n{selected_table} 不支援股票代碼篩選，將匯出全部資料")
            
            # 獲取輸出檔案名稱
            suggested_filename = f"{selected_table_info['chinese_name']}.csv"
            
            while True:
                try:
                    output_filename = input(f"\n💾 請輸入輸出檔案名稱 (建議: {suggested_filename}): ").strip()
                    
                    if not output_filename:
                        output_filename = suggested_filename
                        print(f"使用建議檔案名稱: {output_filename}")
                        break
                    
                    if not output_filename.lower().endswith('.csv'):
                        output_filename += '.csv'
                        print(f"已自動添加 .csv 副檔名: {output_filename}")
                    else:
                        print(f"輸出檔案名稱: {output_filename}")
                    
                    break
                except KeyboardInterrupt:
                    print("\n操作已取消")
                    return
            
            # 執行匯出
            print(f"\n開始匯出數據...")
            print(f"表格: {selected_table_info['chinese_name']} ({selected_table})")
            print(f"檔案: {output_filename}")
            print(f"保存位置: csv_exports/{output_filename}")
            if stock_ids:
                print(f"股票代碼: {', '.join(stock_ids)}")
            
            # 使用 Controller 執行匯出
            success = self.controller.export_csv(selected_table, output_filename, stock_ids)
            
            if success:
                print(f"\n數據匯出成功！")
                print(f"檔案已保存為: csv_exports/{output_filename}")
                print("\n提示: 檔案使用 UTF-8 BOM 編碼，Excel 可以正確顯示中文")
                print(f"提示: 所有匯出檔案都保存在 csv_exports/ 資料夾中")
            else:
                print(f"\n數據匯出失敗！請檢查日誌了解詳細錯誤訊息")
        
        except Exception as e:
            print(f"\n匯出過程中發生錯誤: {e}")
            logger.error(f"CSV 匯出失敗: {e}")
        
        input("\n按 Enter 鍵返回主選單...")

    def handle_special_options(self, choice):
        """處理特殊選項"""
        if choice == 'status':
            print("顯示收集器狀態...")
            self.show_collector_status()
            return True
        elif choice == 'reset_progress':
            print("重置下載進度...")
            self.reset_download_progress()
            return True
        elif choice == 'drop_database':
            print("刪除所有資料庫表格...")
            self.drop_all_database_tables()
            return True
        elif choice == 'export_csv':
            self.handle_csv_export()
            return True
        return False

    def display_welcome_message(self):
        """顯示歡迎訊息"""
        # 獲取狀態
        status = self.controller.get_system_status()
        
        print("\n" + "="*80)
        print("歡迎使用 StockHunter FinMind 數據收集系統")
        print("="*80)
        print(f"   Token Mode: {status['token_mode']} ({status['token_count']} Active)")
        if not status['db_connected']:
            print("   警告: 資料庫連接失敗")
        print("="*80)
        print("專業的台股數據收集與分析工具")
        print("支援技術面、籌碼面、基本面全方位數據收集")
        print("支援斷點續傳，確保數據收集完整性")
        print("="*80)

    def display_goodbye_message(self):
        """顯示再見訊息"""
        print("感謝使用 StockHunter FinMind！")
        print("數據收集系統已安全退出")
        print("如有問題，請檢查日誌檔案或聯繫開發團隊")
