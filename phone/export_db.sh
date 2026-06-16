#!/usr/bin/env bash

# ==============================================================================
# StockHunter Finmind - 手機端一鍵導出 PostgreSQL 資料庫腳本
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 定位腳本所在目錄，並切換至專案根目錄
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

BACKUP_FILE="/data/data/com.termux/files/home/StockHunter_Finmind/stock_hunter_backup.dump"

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}💾 StockHunter 手機資料庫一鍵導出程序${NC}"
echo -e "${GREEN}===============================================${NC}"

# 1. 確保資料庫已啟動 (導出資料需要連線資料庫)
echo -e "${BLUE}ℹ️  正在確保 PostgreSQL 資料庫已啟動...${NC}"
su -c "env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/var/lib/postgresql/pg.log start"

# 等待資料庫就緒
sleep 2

# 2. 執行資料庫打包備份
echo -e "${BLUE}ℹ️  正在打包導出資料庫 stock_hunter...${NC}"
su u0_a166 -c "env PATH=/data/data/com.termux/files/usr/bin pg_dump -d stock_hunter -F c -b -v -f ${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 資料庫打包成功！${NC}"
    echo -e "💾 備份檔案位置：${YELLOW}${BACKUP_FILE}${NC}"
    echo ""
    echo -e "${GREEN}------------------------------------------------------------${NC}"
    echo -e "${GREEN}💻 電腦端接收資料指引：${NC}"
    echo -e "  請在您的電腦（Mac）終端機中，執行以下指令將備份抓回電腦："
    echo -e "  ${YELLOW}adb pull /data/data/com.termux/files/home/StockHunter_Finmind/stock_hunter_backup.dump ./ ${NC}"
    echo -e ""
    echo -e "  抓回電腦後，在電腦終端機執行以下指令還原至電腦的 PostgreSQL："
    echo -e "  ${YELLOW}pg_restore -d stock_hunter -v ./stock_hunter_backup.dump ${NC}"
    echo -e "${GREEN}------------------------------------------------------------${NC}"
else
    echo -e "${RED}❌ 資料庫打包失敗，請檢查 pg.log 日誌。${NC}"
fi
