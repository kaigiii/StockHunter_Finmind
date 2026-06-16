#!/usr/bin/env bash

# ==============================================================================
# StockHunter Finmind - 手機端一鍵啟動互動式選單介面 (TUI)
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 定位腳本所在目錄，並切換至專案根目錄
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}🎮 StockHunter 互動式選單啟動程序${NC}"
echo -e "${GREEN}===============================================${NC}"

# 1. 確保資料庫已啟動 (互動選單運行需要連線資料庫)
echo -e "${BLUE}ℹ️  正在確保 PostgreSQL 資料庫已啟動...${NC}"
su -c "env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/var/lib/postgresql/pg.log start"

# 等待資料庫就緒
sleep 2

# 2. 啟動互動選單 (在目前 Termux 環境執行，確保上網權限與 TUI 輸入輸出正常)
echo -e "${GREEN}✅ 資料庫伺服器啟動成功，正在開啟互動選單介面...${NC}"
echo ""

# 執行 cli_entry.py (不帶參數，進入互動選單模式)
python3 cli_entry.py
