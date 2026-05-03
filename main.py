import subprocess
import sys
import os

from colorama import init, Fore, Style

import tkinter as tk
import tkinter.messagebox as tkm

from threading import Thread

class MainWindow:
    def __init__(self, root: tk.Tk):
        # windows
        self.root = root
        self.root.title("Pyinstaller GUI")
        self.root.geometry("600x600")

        # labels
        self.title = tk.Label(self.root, 
                              width = 500, 
                              height = 10, 
                              text = "Pyinstaller GUI", 
                              font = (FONT_PATH, )
                              )
        self.title.pack()



def resourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def showCode(msg):  # show running code
    # Style.BRIGHT + 
    print(Fore.BLACK + f"[Executing] {msg}")

def showInfo(msg, msgboxTitle = ""):
    printMsg = f"[info] {msg}"
    print(Fore.CYAN + printMsg)
    if msgboxTitle:
        tkm.showinfo(msgboxTitle, printMsg)

def showError(msg, msgboxTitle = ""):
    printMsg = f"[Error] {msg}"
    print(Fore.LIGHTRED_EX + printMsg)
    if msgboxTitle:
        tkm.showerror(msgboxTitle, printMsg)

def runCommand(commandList: list):  # return tuple: (isSuccessful, returnCode)
    try:
        result = subprocess.run(
            commandList, 
            capture_output=True,    # 擷取輸出文字
            text=True,    # 將輸出轉換為字串
            check=True,   # 執行有問題會raise Error
            env = ENV    # 自行注入環境變數
        )

        showCode(" ".join(commandList))
        
        showInfo("Executed successfully")
        showInfo(f"Output: {result.stdout}")
        return True, 0

    except subprocess.CalledProcessError as e:
        showError(f"Execution failed, error code: {e.returncode}")
        showError(f"Error message: {e.stderr if e.stderr else e.stdout}", "Error")
        return False, e.returncode
    except Exception as e:
        showError("Execution failed with a unexcepted error")
        showError(Fore.LIGHTRED_EX + str(e), "Error")
        return False, -1

def testPyinstaller():
    showInfo("Testing Pyinstaller...")
    isSuccessful, _ = runCommand([PYTHON_PATH, "-m", "PyInstaller", "--version"])
    if isSuccessful:
        showInfo("Pyinstaller tested successfully")
    else:
        showError("Because the Pyinstaller couldn't execute successfully, the app can't run now. Please try it later or contact the developer", "Error")
        sys.exit()

def main():
    init()  # colorama 的 initialize
    testPyinstaller()

    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


PYTHON_PATH = resourcePath(r"python_core/python.exe")
PYINSTALLER_PATH = resourcePath(r"python_core/Scripts/pyinstaller.exe")
CORE_PATH = resourcePath("python_core")
LIB_PATH = os.path.join(CORE_PATH, "Lib", "site-packages")

FONT_PATH

# 建立自定義環境變數
ENV = os.environ.copy()
ENV["PATH"] = CORE_PATH + os.pathsep + ENV.get("PATH", "")  # 確保PATH包含python_core 讓pyinstaller.exe可以找到python313.dll
ENV["PYTHONPATH"] = LIB_PATH    # 確保PYTHONPATH 包含site-packages



if __name__ == "__main__":
    main()