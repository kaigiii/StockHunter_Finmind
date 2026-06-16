# StockHunter Finmind - Android Termux 部署安裝指南

本指南詳細記錄如何將本專案從 0 開始部署到已連接的 Android 手機 (Termux 環境) 上。

---

## 📋 事前準備
1. 手機已開啟 **USB 偵錯**，並使用傳輸線連接至 Mac。
2. 手機已安裝 **Termux App** (強烈建議從 F-Droid 官網下載，請勿使用 Google Play 舊版本)。
3. 手機已取得 **Root 權限** (Magisk 或 APatch)，此權限用來啟動 PostgreSQL 資料庫。

---

## 🛠️ 第一步：安裝 Termux 系統套件
在手機 Termux 中（或透過電腦 ADB shell）執行以下指令，更新套件源並安裝編譯與資料庫所需套件：

```bash
# 更新套件庫
pkg update && pkg upgrade -y

# 啟用 TUR 社群套件庫 (用來下載預編譯好的 NumPy/Pandas)
pkg install tur-repo -y

# 安裝資料庫、Python、編譯器與加速庫
pkg install git python clang make postgresql python-numpy python-pandas termux-api rust libxml2 libxslt python-lxml python-psutil -y
```

---

## 第二步：複製專案至手機
將專案檔案從電腦推送到手機 Termux 的 Home 目錄中：

```bash
# 1. 透過電腦終端機將專案推送到手機臨時資料夾
adb push . /data/local/tmp/StockHunter_Finmind

# 2. 透過 run-as 將專案複製到 Termux 的私有資料夾中並清除臨時檔
adb shell "run-as com.termux cp -r /data/local/tmp/StockHunter_Finmind /data/data/com.termux/files/home/ && rm -rf /data/local/tmp/StockHunter_Finmind"
```

---

## 🐍 第三步：安裝 Python 依賴包 ( requirements.txt )
由於 Pydantic 的底層核心是 Rust 寫的，在 Android 上編譯時必須限制為**單執行緒**以防檔案寫入死鎖。請執行以下複合指令進行安裝：

```bash
adb shell "run-as com.termux env -i HOME=/data/data/com.termux/files/home PATH=/data/data/com.termux/files/usr/bin LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib TMPDIR=/data/data/com.termux/files/usr/tmp CARGO_TARGET_DIR=/data/data/com.termux/files/usr/tmp/cargo-target ANDROID_API_LEVEL=24 CARGO_BUILD_JOBS=1 /data/data/com.termux/files/usr/bin/bash -c 'cd ~/StockHunter_Finmind && pip install --no-cache-dir -r requirements.txt'"
```

---

## 🗄️ 第四步：初始化資料庫

### 1. 初始化資料庫資料夾
```bash
adb shell "su u0_a166 -c 'env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp initdb -D /data/data/com.termux/files/usr/var/lib/postgresql --nosync --locale=C'"
```

### 2. 啟動 PostgreSQL 服務
```bash
adb shell "su u0_a166 -c 'env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin TMPDIR=/data/data/com.termux/files/usr/tmp pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/var/lib/postgresql/pg.log start'"
```

### 3. 建立角色與資料庫 (對齊 .env 設定)
```bash
# 建立 superuser 角色 finmind_user
adb shell "su u0_a166 -c 'env PATH=/data/data/com.termux/files/usr/bin psql -d postgres -c \"CREATE ROLE finmind_user WITH LOGIN SUPERUSER PASSWORD '\''FINMIND_PASSWORD'\'';\"'"

# 建立數據庫 stock_hunter
adb shell "su u0_a166 -c 'env PATH=/data/data/com.termux/files/usr/bin createdb -O finmind_user stock_hunter'"
```

### 4. 初始化資料表結構
```bash
adb shell "su u0_a166 -c 'env HOME=/data/data/com.termux/files/home PATH=/data/data/com.termux/files/usr/bin LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib PYTHONPATH=/data/data/com.termux/files/home/StockHunter_Finmind bash -c \"cd ~/StockHunter_Finmind && python3 core/database.py\"'"
```

---

## 📲 第五步：設定快捷指令別名 (Aliases)

執行以下指令在 Termux 中加入快速啟動捷徑，並建立載入關聯：

```bash
# 1. 寫入快捷指令至 ~/.bashrc
adb shell "su u0_a166 -c 'echo -e \"alias stock=\\\"cd ~/StockHunter_Finmind && bash run_phone.sh\\\"\nalias stock-reset=\\\"cd ~/StockHunter_Finmind && bash reset_phone.sh\\\"\nalias stock-export=\\\"cd ~/StockHunter_Finmind && bash export_db.sh\\\"\nalias stock-ui=\\\"cd ~/StockHunter_Finmind && bash run_ui.sh\\\"\nalias stock-web=\\\"cd ~/StockHunter_Finmind && bash run_web.sh\\\"\" > /data/data/com.termux/files/home/.bashrc'"

# 2. 建立引導讀取的 ~/.bash_profile
adb shell "su u0_a166 -c 'echo -e \"if [ -f ~/.bashrc ]; then\n    . ~/.bashrc\nfi\" > /data/data/com.termux/files/home/.bash_profile'"

# 3. 修正這兩個設定檔的所有權與權限
adb shell "su -c 'chown u0_a166:u0_a166 /data/data/com.termux/files/home/.bashrc /data/data/com.termux/files/home/.bash_profile && chmod 600 /data/data/com.termux/files/home/.bashrc /data/data/com.termux/files/home/.bash_profile'"
```

---

## 🏃 部署完成！如何運行
未來只要打開手機的 **Termux App**，輸入以下捷徑指令：
* **`stock`**：一鍵開啟資料庫並啟動爬蟲（支援中途斷點續傳）。
* **`stock-reset`**：一鍵將資料庫內的下載進度清空歸零（以便下一次進行完整重新下載）。
* **`stock-export`**：一鍵打包 PostgreSQL 資料庫為備份檔，便於傳輸回電腦還原。
* **`stock-ui`**：一鍵啟動互動式選單介面（圖形化終端介面）。
* **`stock-web`**：一鍵啟動網頁儀表板服務（Web Dashboard）。
