import subprocess
import sys
import os
'''
import tkinter as tk
import tkinter.messagebox as tkm
'''
from threading import Thread

def resourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def showInfo(msg):
    print(f"[info] {msg}")

def showError(msg):
    print(f"[Error] {msg}")

def runCommand(commandList: list):  # return tuple: (isSuccessful, returnCode)
    try:
        result = subprocess.run(
            commandList, 
            capture_output=True,    # 擷取輸出文字
            text=True,    # 將輸出轉換為字串
            check=True    # 執行有問題會raise Error
        )
        
        showInfo("Executed successfully")
        showInfo(f"Output: {result.stdout}")
        return True, 0

    except subprocess.CalledProcessError as e:
        showError(f"Execution failed, error code: {e.returncode}")
        showError(f"Error message: {e.stderr}")
        return False, e.returncode
    except Exception as e:
        showError("Execution failed with a unexcepted error")
        showError(str(e))
        return False, -1

def testPyinstaller():
    showInfo("Testing Pyinstaller...")
    isSuccessful, _ = runCommand([PYINSTALLER_PATH, "--version"])
    if isSuccessful:
        showInfo("Pyinstaller tested successfully")

def main():
    testPyinstaller()


PYINSTALLER_PATH = resourcePath(r"python_core/Scripts/pyinstaller.exe")


if __name__ == "__main__":
    main()