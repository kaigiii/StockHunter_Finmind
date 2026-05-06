# StockHunter FinMind

一個專為台股投資人設計的高效能數據收集系統，基於 FinMind API，支援多帳號併發下載、斷點續傳與自動錯誤處理。

## 核心功能

*   **全方位數據收集**：涵蓋技術面、籌碼面、基本面等 28 種以上的台股數據。
*   **高速併發 (Revolver Mode)**：支援設定多個 FinMind API Token 進行輪詢，提高收集效率。
*   **斷點續傳**：所有數據皆寫入 PostgreSQL 資料庫，程式可隨時中斷並從上次進度繼續，不需重新下載。
*   **穩定健壯**：內建資料庫連線池與自動重試機制，確保數據完整性。

## API 限制與 IP 使用建議

FinMind API 免費版限制每小時 600 次請求。
**重要提示**：FinMind 會同時檢查 Token 與來源 IP。這意味著即使您擁有多個 Token，如果它們都來自這同一個 IP，仍然會很快遇到速率限制 (402 Rate Limit)。

**建議使用方式**：
1.  **單一 Token 穩定使用**：建議一次使用一個 API Token 即可。
2.  **切換 IP 繼續使用**：如果遇到 `402 Rate Limit` 錯誤，最有效的方法是 **切換您的網路 IP** (例如：重連 VPN、重啟路由器、或切換手機熱點)，然後重新執行程式即可繼續下載。

程式內建了 402 錯誤偵測，遇到限制時會自動暫停等待。

---

## 支援的數據收集器 (共 28 種)

本系統將收集器分為三大類，您可以使用 ID 或分類名稱進行指令呼叫：

### 1. 技術面資料 (Technical)
1.  **台股總覽** (TaiwanStockInfo): 股票基本資料、上市櫃類別
2.  **台股總覽(含權證)** (TaiwanStockInfoWithWarrant): 包含權證的完整代碼列表
3.  **台股交易日** (TaiwanStockTradingDate): 歷年開休市日期表
4.  **股價日成交資訊** (TaiwanStockPrice): 每日開高低收、成交量
5.  **個股PER、PBR資料表** (TaiwanStockPER): 本益比、股價淨值比、殖利率
6.  **每5秒委託成交統計** (TaiwanStockStatisticsOfOrderBookAndTrade): 高頻交易數據
7.  **加權指數** (TaiwanVariousIndicators5Seconds): 大盤指數與成交量
8.  **當日沖銷交易標的及成交量值** (TaiwanStockDayTrading): 當沖交易統計
9.  **加權、櫃買報酬指數** (TaiwanStockTotalReturnIndex): 還原權值指數

### 2. 籌碼面資料 (Chip)
10. **個股融資融劵表** (TaiwanStockMarginPurchaseShortSale): 融資融券餘額
11. **台灣市場整體融資融劵表** (TaiwanStockTotalMarginPurchaseShortSale): 大盤整體融資券
12. **法人買賣表** (TaiwanStockInstitutionalInvestorsBuySell): 外資、投信、自營商買賣超
13. **台灣市場整體法人買賣表** (TaiwanStockTotalInstitutionalInvestors): 三大法人整體買賣金額
14. **外資持股表** (TaiwanStockShareholding): 外資持股比例與股數
15. **借券成交明細** (TaiwanStockSecuritiesLending): 借券餘額與成交量
16. **暫停融券賣出表(融券回補日)** (TaiwanStockMarginShortSaleSuspension): 融券回補日期查詢
17. **信用額度總量管制餘額表** (TaiwanDailyShortSaleBalances): 信用交易額度監控
18. **證券商資訊表** (TaiwanSecuritiesTraderInfo): 券商分點資料

### 3. 基本面資料 (Fundamental)
19. **綜合損益表** (TaiwanStockFinancialStatements): EPS、營收、淨利等季報資料
20. **資產負債表** (TaiwanStockBalanceSheet): 資產、負債、股東權益
21. **現金流量表** (TaiwanStockCashFlowsStatement): 營業、投資、籌資現金流
22. **股利政策表** (TaiwanStockDividend): 歷年配股配息資料
23. **除權除息結果表** (TaiwanStockDividendResult): 除權息參考價與缺口
24. **月營收表** (TaiwanStockMonthRevenue): 每月營收與年增率
25. **減資恢復買賣參考價格** (TaiwanStockCapitalReductionReferencePrice): 減資後參考價
26. **台灣股票下市櫃表** (TaiwanStockDelisting): 下市櫃股票清單與日期
27. **台股分割後參考價** (TaiwanStockSplitPrice): 股票分割資訊
28. **台股變更面額恢復買賣參考價格** (TaiwanStockParValueChange): 面額變更資訊

---

## 安裝說明

1.  **Clone 專案**
    ```bash
    git clone https://github.com/kaigiii/StockHunter_Finmind.git
    cd StockHunter_Finmind
    ```

2.  **安裝依賴**
    建議使用 Python 3.10 以上版本
    ```bash
    pip install -r requirements.txt
    ```

3.  **設定環境變數 (.env)**
    請複製 `.env.example` 為 `.env` 並填入資料庫與 Token 資訊。

---

## 快速啟動

專案支援三種運行模式，滿足從視覺化操作到自動化腳本的所有需求：

### A. 專業網頁儀表板 (Web Dashboard)
提供視覺監控、即時日誌與全系統參數設定。
```bash
uv run --with-requirements requirements.txt python3 app_server.py
```
*   **入口網址**：`http://localhost:8000` (預設)

### B. 極簡互動模式 (CLI Mode)
適合伺服器環境或偏好互動式終端操作的使用者。
```bash
python3 cli_entry.py
```
*   **特色**：提供互動選單，可快速選擇要抓取的模組分類。

### C. 指令自動化模式 (Headless CLI)
**不需透過介面**，適合排程任務 (Cron Job) 或腳本調用。支援透過參數直接指定收集模組與日期範圍。
```bash
# 語法：python3 cli_entry.py --ids [ID清單/分類] --start [日期] --custom
python3 cli_entry.py --ids 1,4,10 --start 2023-01-01 --custom
```
*   **常用範例**：
    *   `--ids all`: 抓取所有 28 個模組。
    *   `--ids technical`: 僅抓取「技術面」分類。
    *   `--ids 4,12 --start 2024-01-01 --custom`: 抓取股價與法人，並強制指定日期。
*   **參數說明**：
    *   `--ids`: 收集器編號（1-28）或分類名稱（technical/chip/fundamental/all）。
    *   `--start`: 自定義開始日期 (YYYY-MM-DD)。
    *   `--end`: 自定義結束日期 (預設為今天)。
    *   `--custom`: 若要使用自定義日期，必須加上此 flag。

---