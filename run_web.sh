#!/usr/bin/env bash

# ==============================================================================
# StockHunter Finmind - 手機端一鍵啟動網頁儀表板 (Web Dashboard)
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}🌐 StockHunter 網頁儀表板啟動程序${NC}"
echo -e "${GREEN}===============================================${NC}"

# 1. 確保資料庫已啟動
echo -e "${BLUE}ℹ️  正在確保 PostgreSQL 資料庫已啟動...${NC}"
su -c "env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/var/lib/postgresql/pg.log start"

# 等待資料庫就緒
sleep 2

# 2. 啟動網頁儀表板 (在目前 Termux 環境執行，確保上網權限)
echo -e "${GREEN}✅ 資料庫伺服器啟動成功，正在啟動 Web 伺服器...${NC}"
echo -e "${YELLOW}💡 提示：啟動後，請在手機瀏覽器打開 http://localhost:8000 即可使用。${NC}"
echo -e "${YELLOW}      若要從電腦瀏覽，請確保您與手機在同一個 Wi-Fi，或使用 ADB 轉發連接埠：${NC}"
echo -e "${BLUE}      adb forward tcp:8000 tcp:8000${NC}"
echo ""

# 執行 app_server.py
python3 app_server.py
