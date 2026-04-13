import subprocess
import sys
import os

import tkinter
import tkinter.messagebox as tkm

from threading import Thread

def resourcePath(relative_path):
    # 獲取資源的絕對路徑 兼容開發環境與 PyInstaller
    try:
        # PyInstaller 建立的臨時資料夾路徑存放在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def showInfo(msg):
    print(f"[info] {msg}")

def showError(msg):
    print(f"[Error] {msg}")


def autoInstallPip():
    try:
        with open(resourcePath("get-pip.py"), "r") as f:
                installCode = f.read()
        eval(installCode)
        showInfo("Pip auto installed successful.")
        # 重新自動安裝pyinstaller
        autoInstallPyinstaller()
    except Exception as e:
        showError(f"Unexcepted Error: {e}")
        tkm.showerror("Unexpected error", f"Error while installing pip. Error message: {e.stderr} / Error code: {e.returncode}. Please try again.")

def autoInstallPyinstaller():
    try:
        result = subprocess.run(
            ["pip", "install", "pyinstaller"], 
            capture_output=True,    # 擷取輸出文字
            text=True,    # 將輸出轉換為字串 而非bytes
            check=True    # 失敗時拋出異常
        )
        showInfo("Pyinstaller installed successful.")
        showInfo(f"Output: {result.stdout[:50]}...")
        # 測試pyinstaller可不可以用
        testPyinstaller()

    except subprocess.CalledProcessError as e:
        showError(f"Execution failed, error code: {e.returncode}")
        showError(f"Error message: {e.stderr}")
        tkm.showerror("Unexpected error", f"Error while installing pyinstaller. Error message: {e.stderr} / Error code: {e.returncode}. Please try again.")

    except FileNotFoundError:
        showInfo("Pip could not be found, trying auto install...")
        autoInstallPip()

def testPyinstaller():
    try:
        result = subprocess.run(
            ["pyinstaller", "--version"], 
            capture_output=True,    # 擷取輸出文字
            text=True,    # 將輸出轉換為字串 而非bytes
            check=True    # 失敗時拋出異常
        )
        showInfo("Pyinstaller ran successful.")
        showInfo(f"Output: {result.stdout[:50]}...")
    
    except subprocess.CalledProcessError as e:
        showError(f"Pyinstaller ran failed, error code: {e.returncode}")
        showError(f"Error message: {e.stderr}")
        tkm.showerror("Unexpected error", f"Unexpected error while testing Pyinstaller.Error message: {e.stderr} / Error code: {e.returncode}. Please try again.")
    
    except FileNotFoundError:
        # 找不到pyinstall 試用pip自動安裝
        autoInstallPyinstaller()


def main():
    testPyinstaller()


if __name__ == "__main__":
    main()