#!/usr/bin/env bash

# ==============================================================================
# StockHunter Finmind - Termux 自動運行與 IP 切換輔助腳本
# ==============================================================================

# 設定顏色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄 (自動取得目前腳本所在位置)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 偵測是否在 Termux 中運行並嘗試取得 Wake Lock
if [ -d "/data/data/com.termux" ]; then
    echo -e "${BLUE}ℹ️  偵測到 Termux 環境，正在嘗試取得 Wake Lock 以防止系統休眠...${NC}"
    if command -v termux-wake-lock &> /dev/null; then
        termux-wake-lock
        echo -e "${GREEN}✅ 已啟用 Wake Lock${NC}"
    else
        echo -e "${YELLOW}⚠️ 找不到 termux-wake-lock 命令，請確保 Termux API 套件已安裝。${NC}"
    fi
fi

# 輔助通知函數 (若有 termux-api 可發送手機通知)
send_notification() {
    local title="$1"
    local message="$2"
    if command -v termux-notification &> /dev/null; then
        termux-notification -t "$title" -c "$message" --id 8888 --type normal
    fi
}

# 判斷模式
MODE="daily"
if [ "$1" == "--history" ]; then
    MODE="history"
fi

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}🚀 StockHunter Termux 數據收集守護程序已啟動${NC}"
echo -e "${GREEN}====================================================${NC}"

if [ "$MODE" == "history" ]; then
    echo -e "運行模式：${YELLOW}補登歷史資料模式 (History Mode)${NC}"
    echo -e "開始日期：將使用各數據收集器之預設歷史起點 (如 2020-01-01)"
    echo -e "進度處理：繼續使用資料庫中的歷史下載進度"
else
    echo -e "運行模式：${YELLOW}每日全新運行模式 (Daily Reset Mode)${NC}"
    echo -e "開始日期：將使用各數據收集器之預設歷史起點 (如 2020-01-01)"
    
    # 在開始新的每日運行前，重置進度清單 (清空 done 記錄)
    # 這樣今天運行時，所有的收集器才會再次被重新執行檢查
    echo -e "正在重置今日進度清冊..."
    python3 -c "from core.collector_engine import CollectorEngine; CollectorEngine().reset_progress()"
    echo -e "${GREEN}✅ 進度清冊已初始化${NC}"
fi
echo ""

while true; do
    echo -e "${BLUE}🕒 [$(date '+%Y-%m-%d %H:%M:%S')] 啟動 Python 收集引擎...${NC}"
    
    # 不限日期模式，直接調用預設開始日期
    python3 cli_entry.py --ids all
    
    # 獲取結束狀態碼
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}🎉 [$(date '+%Y-%m-%d %H:%M:%S')] 所有數據收集成功完成！${NC}"
        send_notification "StockHunter 任務完成" "今天的台股數據收集已順利結束！"
        break
        
    elif [ $EXIT_CODE -eq 42 ]; then
        echo -e "\n${RED}🛑 [$(date '+%Y-%m-%d %H:%M:%S')] 偵測到 API 限額已達上限！${NC}"
        send_notification "StockHunter API 上限" "已達 API 額度限制，請開關飛航模式更換 IP。"
        
        echo -e "${YELLOW}------------------------------------------------------------${NC}"
        echo -e "${YELLOW}💡 請手動執行以下操作更換 IP：${NC}"
        echo -e "  1. 下拉手機通知欄，${BLUE}開啟「飛航模式」${NC}，等待 3 秒。"
        echo -e "  2. ${BLUE}關閉「飛航模式」${NC}，確保行動網路 (4G/5G) 連線恢復。"
        echo -e "  3. 返回此畫面，${GREEN}按任意鍵繼續${NC} (程式將自動從中斷的個股/日期續傳)。"
        echo -e "  *(若想結束此腳本，請按 ${RED}Ctrl + C${NC} 退出)*"
        echo -e "${YELLOW}------------------------------------------------------------${NC}"
        
        # 讀取使用者按鍵
        read -n 1 -s -r
        echo -e "\n${GREEN}🔄 已檢測到按鍵，正在重試執行...${NC}"
        
    else
        echo -e "\n${RED}❌ [$(date '+%Y-%m-%d %H:%M:%S')] 程式異常結束 (退出碼: $EXIT_CODE)${NC}"
        send_notification "StockHunter 執行錯誤" "程式異常中斷，退出碼: $EXIT_CODE"
        exit $EXIT_CODE
    fi
done

# 釋放 Wake Lock
if [ -d "/data/data/com.termux" ] && command -v termux-wake-unlock &> /dev/null; then
    termux-wake-unlock
    echo -e "${BLUE}ℹ️  已釋放 Wake Lock${NC}"
fi
