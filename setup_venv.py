#!/usr/bin/env python3
"""
虛擬環境設置腳本
跨平台版本，適用於 macOS、Linux 和 Windows
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, shell=False):
    """執行命令並返回結果"""
    try:
        if shell:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """檢查 Python 版本"""
    print("檢查 Python 版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python 版本過低: {version.major}.{version.minor}")
        print("需要 Python 3.7 或更高版本")
        return False
    
    print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True

def create_venv():
    """創建虛擬環境"""
    print("創建虛擬環境...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("⚠️  虛擬環境已存在，跳過創建")
        return True
    
    success, stdout, stderr = run_command([sys.executable, "-m", "venv", "venv"])
    if success:
        print("✅ 虛擬環境創建成功")
        return True
    else:
        print(f"❌ 虛擬環境創建失敗: {stderr}")
        return False

def get_activate_command():
    """獲取啟動虛擬環境的命令"""
    system = platform.system().lower()
    
    if system == "windows":
        return "venv\\Scripts\\activate.bat"
    else:
        return "source venv/bin/activate"

def get_pip_command():
    """獲取 pip 命令"""
    system = platform.system().lower()
    
    if system == "windows":
        return "venv\\Scripts\\pip"
    else:
        return "venv/bin/pip"

def install_dependencies():
    """安裝依賴"""
    print("安裝 Python 依賴...")
    
    pip_cmd = get_pip_command()
    
    # 升級 pip
    print("升級 pip...")
    success, stdout, stderr = run_command([pip_cmd, "install", "--upgrade", "pip"])
    if success:
        print("✅ pip 升級成功")
    else:
        print(f"⚠️  pip 升級失敗: {stderr}")
    
    # 安裝依賴
    print("安裝項目依賴...")
    success, stdout, stderr = run_command([pip_cmd, "install", "-r", "requirements.txt"])
    if success:
        print("✅ 依賴安裝成功")
        return True
    else:
        print(f"❌ 依賴安裝失敗: {stderr}")
        return False

def main():
    """主函數"""
    print("=== StockHunter FinMind 虛擬環境設置腳本 ===")
    print(f"作業系統: {platform.system()} {platform.release()}")
    print()
    
    # 檢查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 創建虛擬環境
    if not create_venv():
        sys.exit(1)
    
    # 安裝依賴
    if not install_dependencies():
        print("⚠️  依賴安裝失敗，但虛擬環境已創建")
        print("請手動安裝依賴: pip install -r requirements.txt")
    
    print()
    print("🎉 虛擬環境設置完成！")
    print()
    
    activate_cmd = get_activate_command()
    print("使用方法：")
    print(f"1. 啟動虛擬環境: {activate_cmd}")
    print("2. 運行主程式: python main.py")
    print("3. 退出虛擬環境: deactivate")
    print()
    
    if platform.system().lower() == "windows":
        print("現在請運行:")
        print(f"  {activate_cmd}")
    else:
        print("現在請運行:")
        print(f"  {activate_cmd}")

if __name__ == "__main__":
    main()
