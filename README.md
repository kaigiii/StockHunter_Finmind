# StockHunter FinMind 🚀

一個專為台股投資人設計的高效能數據收集系統，基於 FinMind API，支援多帳號併發下載、斷點續傳與自動錯誤處理。

## 🌟 核心功能

*   **全方位數據收集**：涵蓋技術面、籌碼面、基本面等 28 種以上的台股數據（股價、法人買賣、財報、除權息...）。
*   **高速併發 (Revolver Mode)**：
    *   支援設定多個 FinMind API Token。
    *   自動輪詢 Token，突破單一帳號每小時 600 次請求的限制。
    *   智慧處理 `402 Rate Limit`，遇到上限自動冷卻並切換 Token。
*   **斷點續傳**：所有數據皆寫入 PostgreSQL 資料庫，程式可隨時中斷並從上次進度繼續。
*   **穩定健壯**：
    *   內建資料庫連線池 (Connection Pooling)。
    *   自動去重複 (Postgres UPSERT)，防止重複資料報錯。
    *   自動處理網路異常與 API 錯誤。

## 🛠️ 安裝說明

1.  **Clone 專案**
    ```bash
    git clone https://github.com/kaigiii/StockHunter_Finmind.git
    cd StockHunter_Finmind
    ```

2.  **安裝依賴**
    建議使用 Python 3.10+
    ```bash
    pip install -r requirements.txt
    ```

3.  **設定環境變數 (.env)**
    請複製 `.env.example` (若無則自行建立 `.env`) 並填入您的資訊：
    ```env
    # 資料庫設定 (PostgreSQL)
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=stock_hunter
    DB_USER=your_username
    DB_PASSWORD=your_password

    # FinMind API Token (可無限新增，格式為 FINMIND_API_TOKEN_X)
    # 前往 https://finmind.github.io/ 註冊免費 Token
    FINMIND_API_TOKEN_1=your_token_1
    FINMIND_API_TOKEN_2=your_token_2
    FINMIND_API_TOKEN_3=your_token_3

    # 下載設定
    # 併發執行緒數 (建議設為 Token 數量 * 2，或是 5-10 之間)
    MAX_WORKERS=5
    
    # 時間範圍設定
    TAIWAN_STOCK_PRICE_START_DATE=2000-01-01
    ```

## 🚀 使用方法

執行主程式：
```bash
python3 main.py
```

程式會顯示互動式選單，您可以選擇：
1.  **選擇收集類別**：技術面、籌碼面、基本面...
2.  **選擇時間範圍**：完整歷史數據 或 自定義範圍。
3.  **開始下載**：程式會自動啟動多執行緒下載，並顯示即時進度條。

## 📂 專案結構

*   `core/`: 核心模組 (資料庫管理、設定檔讀取)。
*   `services/`: 服務層 (API 轉輪、速率限制)。
*   `collectors/`: 數據收集器實作 (按領域分類)。
    *   `technical/`: 技術指標 (股價、成交量)。
    *   `chip/`: 籌碼指標 (法人、融資券)。
    *   `fundamental/`: 基本面 (財報、營收)。
*   `ui/`: 命令行介面 (CLI) 邏輯。

## ⚠️ 注意事項

*   FinMind 免費版 API 限制每小時 600 次請求。本系統的 **Revolver Mode** 可透過多 Token 繞過此限制，但請勿濫用。
*   若遇到 `402 Rate Limit`，程式會自動暫停等待（全域冷卻），請耐心等候程式自動恢復。

## 📝 License

MIT License
