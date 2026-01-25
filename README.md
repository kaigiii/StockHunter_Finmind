# StockHunter FinMind

一個專為台股投資人設計的高效能數據收集系統，基於 FinMind API，支援多帳號併發下載、斷點續傳與自動錯誤處理。

## 核心功能

*   **全方位數據收集**：涵蓋技術面、籌碼面、基本面等 28 種以上的台股數據。
*   **高速併發 (Revolver Mode)**：支援設定多個 FinMind API Token 進行輪詢，提高收集效率。
*   **斷點續傳**：所有數據皆寫入 PostgreSQL 資料庫，程式可隨時中斷並從上次進度繼續，不需重新下載。
*   **穩定健壯**：內建資料庫連線池與自動重試機制，確保數據完整性。

## API 限制與 IP 使用建議

FinMind API 免費版限制每小時 600 次請求。
**重要提示**：FinMind 會同時檢查 Token 與來源 IP。這意味著即使您擁有多個 Token，如果它們都來自這同一個 IP (例如公司或家裡的同一個 WiFi)，仍然會很快遇到速率限制 (402 Rate Limit)。

**建議使用方式**：
1.  **單一 Token 穩定使用**：建議一次使用一個 API Token 即可。
2.  **切換 IP 繼續使用**：如果遇到 `402 Rate Limit` 或 `402 Too Many Requests` 錯誤，最有效的方法是**切換您的網路 IP** (例如：重連 VPN、重啟路由器、或切換手機熱點)，然後重新執行程式即可繼續下載。

程式內建了 402 錯誤偵測，遇到限制時會自動暫停等待。若您不想等待冷卻時間，請直接停止程式，切換 IP 後重啟即可。

## 支援的數據收集器

本系統支援以下 28 種數據收集器：

### 技術面資料 (Technical)
1.  **台股總覽** (TaiwanStockInfo): 股票基本資料、上市櫃類別
2.  **台股總覽(含權證)** (TaiwanStockInfoWithWarrant): 包含權證的完整代碼列表
3.  **台股交易日** (TaiwanStockTradingDate): 歷年開休市日期表
4.  **股價日成交資訊** (TaiwanStockPrice): 每日開高低收、成交量
5.  **個股PER、PBR資料表** (TaiwanStockPER): 本益比、股價淨值比、殖利率
6.  **每5秒委託成交統計** (TaiwanStockStatisticsOfOrderBookAndTrade): 高頻交易數據
7.  **加權指數** (TaiwanVariousIndicators5Seconds): 大盤指數與成交量
8.  **當日沖銷交易標的及成交量值** (TaiwanStockDayTrading): 當沖交易統計
9.  **加權、櫃買報酬指數** (TaiwanStockTotalReturnIndex): 還原權值指數

### 籌碼面資料 (Chip)
10. **個股融資融劵表** (TaiwanStockMarginPurchaseShortSale): 融資融券餘額
11. **台灣市場整體融資融劵表** (TaiwanStockTotalMarginPurchaseShortSale): 大盤整體融資券
12. **法人買賣表** (TaiwanStockInstitutionalInvestorsBuySell): 外資、投信、自營商買賣超
13. **台灣市場整體法人買賣表** (TaiwanStockTotalInstitutionalInvestors): 三大法人整體買賣金額
14. **外資持股表** (TaiwanStockShareholding): 外資持股比例與股數
15. **借券成交明細** (TaiwanStockSecuritiesLending): 借券餘額與成交量
16. **暫停融券賣出表(融券回補日)** (TaiwanStockMarginShortSaleSuspension): 融券回補日期查詢
17. **信用額度總量管制餘額表** (TaiwanDailyShortSaleBalances): 信用交易額度監控
18. **證券商資訊表** (TaiwanSecuritiesTraderInfo): 券商分點資料

### 基本面資料 (Fundamental)
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
    請複製 `.env.example` 為 `.env` 並填入資料庫與 Token 資訊：
    ```env
    # 資料庫設定 (PostgreSQL)
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=stock_hunter
    DB_USER=your_username
    DB_PASSWORD=your_password

    # FinMind API Token
    # 前往 https://finmind.github.io/ 註冊免費 Token
    FINMIND_API_TOKEN_1=your_token_here
    
    # 併發設定
    MAX_WORKERS=5
    ```

## 使用方法

執行主程式：
```bash
python3 main.py
```

依照畫面選單操作：
1.  輸入收集器對應的編號 (例如 `4` 代表股價)。
2.  選擇時間範圍 (完整下載 或 自定義範圍)。
3.  程式將自動開始下載並存入資料庫。

## 專案結構

*   `core/`: 核心模組 (資料庫、控制器)
*   `services/`: 服務層 (API 管理、匯出服務)
*   `collectors/`: 各類數據收集器
*   `ui/`: 使用者介面邏輯
