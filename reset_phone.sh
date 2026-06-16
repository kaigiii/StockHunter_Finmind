#!/usr/bin/env bash

# ==============================================================================
# StockHunter Finmind - 手機端重置今日進度腳本 (僅重置，不下載)
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}🔄 StockHunter 手機端進度重置程序${NC}"
echo -e "${GREEN}===============================================${NC}"

# 1. 確保資料庫已啟動 (重置進度需要寫入資料庫)
echo -e "${BLUE}ℹ️  正在確保 PostgreSQL 資料庫已啟動...${NC}"
su -c "env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/var/lib/postgresql/pg.log start"

# 等待資料庫就緒
sleep 2

# 2. 執行重置進度代碼
echo -e "${BLUE}ℹ️  正在清除資料庫中的下載進度紀錄...${NC}"
python3 -c "from core.collector_engine import CollectorEngine; CollectorEngine().reset_progress()"

echo -e "${GREEN}✅ 進度清冊已歸零完成！下次執行抓取時將會從頭開始。${NC}"
echo -e "${YELLOW}💡 請輸入 'stock' 指令開始全新抓取。${NC}"
