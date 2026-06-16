# StockHunter Finmind - Termux 部署問題與解決方案日誌 (de_bug)

本檔案記錄了在 Android (Termux) 環境下部署 StockHunter 系統時所遇到的所有錯誤、成因分析及具體解決方法。

---

## 1. NumPy & Pandas 編譯極慢且報錯 (`lapack` 缺失)
* **問題描述**：執行 `pip install` 時，編譯 `numpy` 與 `pandas` 會因為缺少 Fortran 編譯器或 `lapack` 庫而失敗，或在手機上因硬體限制編譯極度緩慢。
* **主要成因**：Android 系統缺乏標準的 Fortran 編譯工具鏈，且直接從原始碼編譯科學計算庫耗費大量系統資源。
* **解決方法**：
  啟用 TUR (Termux User Repository) 並直接安裝 Termux 社群預編譯好的二進位包：
  ```bash
  pkg install tur-repo
  pkg install python-numpy python-pandas
  ```

---

## 2. Maturin & Pydantic-Core 找不到編譯環境變數
* **問題描述**：Rust 編譯器 (Cargo) 在編譯 `maturin` 和 `pydantic-core` 時崩潰，提示 `HOME` 未設置或缺少 `ANDROID_API_LEVEL`。
* **主要成因**：使用 `env -i` 清理環境變數時，將 Cargo 運行時所需的關鍵變數也一併清空了。
* **解決方法**：
  在執行命令的環境中，手動補回這些關鍵變數：
  ```bash
  env HOME=/data/data/com.termux/files/home ANDROID_API_LEVEL=24 ...
  ```

---

## 3. Pydantic-Core 編譯衝突 (`Text file busy (os error 26)`)
* **問題描述**：編譯 `pydantic-core` 依賴庫 `pyo3-ffi` 時，Cargo 拋出 `Text file busy` 錯誤並中斷。
* **主要成因**：Android 的檔案系統緩存機制在多核心並行編譯時，若多個執行緒同時讀寫/執行相同的臨時建置腳本，會觸發檔案鎖定保護。
* **解決方法**：
  限制 Cargo 的並行編譯數為 `1`（單執行緒順序編譯），雖然速度較慢但可保證編譯安全完成：
  ```bash
  env CARGO_BUILD_JOBS=1 pip install pydantic-core
  ```

---

## 4. 再次安裝 requirements.txt 時重新編譯 `pydantic-core`
* **問題描述**：單獨手動安裝完 `pydantic-core` 後，執行整個 `requirements.txt` 安裝仍會重新下載編譯，並再次因多執行緒鎖定而報錯。
* **主要成因**：`requirements.txt` 中的 `fastapi` 依賴鏈解析出的 `pydantic` 指定要求特定版本的 `pydantic-core==2.46.4`，與手動安裝的 `2.47.0` 不符。
* **解決方法**：
  強制在執行 `requirements.txt` 安裝時，同樣套用限制編譯數環境變數：
  ```bash
  env CARGO_BUILD_JOBS=1 pip install -r requirements.txt
  ```

---

## 5. PostgreSQL `initdb` 凍結在 `selecting default "max_connections"`
* **問題描述**：執行 `initdb` 初始化資料庫時，程序會永久停在 `selecting default "max_connections"`。
* **主要成因**：Android 系統為了防範漏洞，在 `run-as` 沙盒（除錯用限制環境）下有極其嚴格的 SELinux 規則，阻斷了 `postgres` 測試進程與 `initdb` 之間的管道通訊 (Pipes) 與 Socket 讀寫。
* **解決方法**：
  使用手機已取得的 Root 權限，改用 `su u0_a166` 啟動。這會在 Magisk/APatch 的寬鬆安全上下文（`u:r:magisk:s0`）中運行，繞過 SELinux 管道限制：
  ```bash
  adb shell "su u0_a166 -c 'initdb -D /data/data/com.termux/files/usr/var/lib/postgresql --nosync --locale=C'"
  ```

---

## 6. 以 `su` 運行時無法連線網路 (`NameResolutionError`)
* **問題描述**：當資料庫以 `su` 成功初始化後，如果將爬蟲腳本也直接用 `su` 啟動，會導致所有 API 請求均回傳 DNS 解析失敗。
* **主要成因**：Android 的網路權限是透過 Linux Group (GID) 來管制的（如網路權限為 `3003(inet)`）。使用 `su` 切換使用者時預設群組被歸為 `root`，失去了 Android 系統賦予一般應用的網路存取群組權限。
* **解決方法**：
  採用 **「分層運行架構」**：
  * **資料庫 (PostgreSQL)**：利用 `su` 啟動在背景（僅監聽本地 127.0.0.1 埠，不需上網）。
  * **爬蟲程式 (Python)**：利用標準的 `run-as com.termux` 啟動，能完整繼承應用的網路權限群組（可自由上網請求 API，並順利連線至本地 PostgreSQL）。

---

## 7. 腳本 shebang `/usr/bin/env` 找不到解析器
* **問題描述**：執行 `./run_termux.sh` 啟動爬蟲時，提示 `bad interpreter: No such file or directory`。
* **主要成因**：Android 不是標準的 Linux 發行版，沒有 `/usr/bin/env` 路徑。
* **解決方法**：
  不直接執行腳本，而是將腳本路徑作為參數傳遞給 Bash 執行：
  ```bash
  bash run_termux.sh
  ```
