#!/usr/bin/env bash

# ==============================================================================
# StockHunter Finmind - 手機端一鍵啟動爬蟲與資料庫腳本
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 定位腳本所在目錄
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}📱 StockHunter 手機端一鍵啟動程序${NC}"
echo -e "${GREEN}===============================================${NC}"

# 1. 啟動 PostgreSQL 資料庫 (使用 su 權限)
echo -e "${BLUE}ℹ️  正在啟動 PostgreSQL 資料庫...${NC}"
echo -e "${YELLOW}💡 提示：如果手機彈出 Root 授權視窗，請點選「允許 (Grant)」。${NC}"

# 執行資料庫啟動指令
su -c "env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/var/lib/postgresql/pg.log start"

# 等待資料庫就緒
echo -e "${BLUE}🕒 等待資料庫載入中 (3 秒)...${NC}"
sleep 3

# 2. 啟動爬蟲 (在目前 Termux 環境執行，確保上網權限)
echo -e "${GREEN}✅ 資料庫伺服器啟動成功，正在載入數據收集引擎...${NC}"
echo ""

# 使用 bash 執行同目錄下的 run_termux.sh，並傳遞所有啟動參數 ($@)
bash run_termux.sh "$@"
