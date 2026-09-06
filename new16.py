import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import shutil
import os
import sys
import re

# ───────────────────────────────────────────────
# 常數定義
# ───────────────────────────────────────────────
WINDOW_TITLE  = "PyInstaller GUI"
WINDOW_W      = 810
WINDOW_H      = 870
WINDOW_MIN_H  = 830
PAD           = 8
BG            = "#F5F5F5"
LOG_BG        = "#1E1E1E"
LOG_FG        = "#D4D4D4"
LOG_ERR       = "#F44747"
LOG_OK        = "#6A9955"

# ───────────────────────────────────────────────
# 通用輔助函式
# ───────────────────────────────────────────────
def browseFile(var, filetypes):
    path = filedialog.askopenfilename(filetypes=filetypes)
    if path:
        var.set(path)

def browseDir(var):
    path = filedialog.askdirectory()
    if path:
        var.set(path)

def openFolder(path):
    if os.path.isdir(path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("開啟資料夾失敗", str(e))

# ───────────────────────────────────────────────
# Spec 檔案解析器
# ───────────────────────────────────────────────
def parseSpec(specPath):
    result = {
        "name": "", "distpath": "", "icon": "",
        "onefile": False, "console": True,
        "addData": [], "hiddenImports": [], "excludes": [],
        "extraFlags": ""
    }
    try:
        with open(specPath, "r", encoding="utf-8") as f:
            content = f.read()

        m = re.search(r"name='([^']*)'", content)
        if m:
            result["name"] = m.group(1)

        m = re.search(r"distpath='([^']*)'", content)
        if m:
            result["distpath"] = m.group(1)

        m = re.search(r"icon=\['([^']*)'\]", content)
        if m:
            result["icon"] = m.group(1)

        result["onefile"] = "EXE(" in content and "BUNDLE(" not in content
        result["console"] = "console=True" in content

        for src, dst in re.findall(r"\('([^']*)',\s*'([^']*)'\)", content):
            result["addData"].append(f"{src}:{dst}")

        m = re.search(r"hiddenimports=\[([^\]]*)\]", content)
        if m:
            result["hiddenImports"] = [
                x.strip().strip("'\"")
                for x in m.group(1).split(",")
                if x.strip().strip("'\"")
            ]

        m = re.search(r"excludes=\[([^\]]*)\]", content)
        if m:
            result["excludes"] = [
                x.strip().strip("'\"")
                for x in m.group(1).split(",")
                if x.strip().strip("'\"")
            ]
    except Exception as e:
        messagebox.showerror("Spec 解析失敗", str(e))

    return result

# ───────────────────────────────────────────────
# 字串清單編輯元件（Hidden Imports / Excludes 共用）
# ───────────────────────────────────────────────
class ListEditor(ttk.Frame):
    def __init__(self, parent, onChange=None, **kw):
        super().__init__(parent, **kw)
        self.onChange = onChange
        self._buildUI()

    def _buildUI(self):
        self.entryVar = tk.StringVar()
        entryRow = ttk.Frame(self)
        entryRow.pack(fill="x", pady=(0, 4))

        ttk.Entry(entryRow, textvariable=self.entryVar).pack(side="left", fill="x", expand=True)
        ttk.Button(entryRow, text="Add",    width=6, command=self._add).pack(side="left", padx=(4, 0))
        ttk.Button(entryRow, text="Remove", width=8, command=self._remove).pack(side="left", padx=(4, 0))

        self.listbox = tk.Listbox(self, height=6, selectmode="single",
                                  bg="white", relief="solid", bd=1)
        self.listbox.pack(fill="both", expand=True)

    def _add(self):
        val = self.entryVar.get().strip()
        if val:
            self.listbox.insert("end", val)
            self.entryVar.set("")
            if self.onChange:
                self.onChange()

    def _remove(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            if self.onChange:
                self.onChange()

    def getItems(self):
        return list(self.listbox.get(0, "end"))

    def setItems(self, items):
        self.listbox.delete(0, "end")
        for item in items:
            self.listbox.insert("end", item)
        if self.onChange:
            self.onChange()

# ───────────────────────────────────────────────
# 附加資料編輯元件（src + dst，支援檔案與目錄）
# ───────────────────────────────────────────────
class DataFileEditor(ttk.Frame):
    def __init__(self, parent, onChange=None, **kw):
        super().__init__(parent, **kw)
        self.onChange = onChange
        self._buildUI()

    def _buildUI(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        ### 新增檔案面板 ###
        fileFrame = ttk.LabelFrame(self, text="Add File", padding=PAD)
        fileFrame.grid(row=0, column=0, sticky="ew", padx=(0, PAD // 2), pady=(0, PAD))
        fileFrame.columnconfigure(1, weight=1)

        ttk.Label(fileFrame, text="Source").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.fileSrcVar = tk.StringVar()
        ttk.Entry(fileFrame, textvariable=self.fileSrcVar).grid(row=0, column=1, sticky="ew")
        ttk.Button(fileFrame, text="Browse", width=7,
                   command=self._browseFileSrc).grid(row=0, column=2, padx=(4, 0))

        ttk.Label(fileFrame, text="Dest").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=(4, 0))
        self.fileDstVar = tk.StringVar()
        ttk.Entry(fileFrame, textvariable=self.fileDstVar).grid(row=1, column=1, sticky="ew", pady=(4, 0))

        ttk.Button(fileFrame, text="Add File", command=self._addFile).grid(
            row=2, column=0, columnspan=3, pady=(6, 0), sticky="e")

        ### 新增目錄面板 ###
        dirFrame = ttk.LabelFrame(self, text="Add Directory", padding=PAD)
        dirFrame.grid(row=0, column=1, sticky="ew", padx=(PAD // 2, 0), pady=(0, PAD))
        dirFrame.columnconfigure(1, weight=1)

        ttk.Label(dirFrame, text="Source").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.dirSrcVar = tk.StringVar()
        ttk.Entry(dirFrame, textvariable=self.dirSrcVar).grid(row=0, column=1, sticky="ew")
        ttk.Button(dirFrame, text="Browse", width=7,
                   command=self._browseDirSrc).grid(row=0, column=2, padx=(4, 0))

        ttk.Label(dirFrame, text="Dest").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=(4, 0))
        self.dirDstVar = tk.StringVar()
        ttk.Entry(dirFrame, textvariable=self.dirDstVar).grid(row=1, column=1, sticky="ew", pady=(4, 0))

        ttk.Button(dirFrame, text="Add Dir", command=self._addDir).grid(
            row=2, column=0, columnspan=3, pady=(6, 0), sticky="e")

        ### 共用條目清單 ###
        listFrame = ttk.LabelFrame(self, text="Entries  (src --> dest)", padding=PAD)
        listFrame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.rowconfigure(1, weight=1)

        self.listbox = tk.Listbox(listFrame, height=5, selectmode="single",
                                  bg="white", relief="solid", bd=1, font=("Consolas", 9))
        self.listbox.pack(fill="both", expand=True)

        ttk.Button(listFrame, text="Remove Selected", command=self._remove).pack(
            anchor="e", pady=(4, 0))

    def _browseFileSrc(self):
        path = filedialog.askopenfilename()
        if path:
            self.fileSrcVar.set(path)
            if not self.fileDstVar.get():    # src 選定後自動帶入預設 dst
                self.fileDstVar.set(".")

    def _browseDirSrc(self):
        path = filedialog.askdirectory()
        if path:
            self.dirSrcVar.set(path)
            if not self.dirDstVar.get():    # src 選定後自動帶入目錄名稱
                self.dirDstVar.set(os.path.basename(path))

    def _addFile(self):
        src = self.fileSrcVar.get().strip()
        dst = self.fileDstVar.get().strip()
        if not src:
            messagebox.showwarning("Missing Source", "Please select a source file.")
            return
        if not dst:
            messagebox.showwarning("Missing Dest", "Please enter a destination path.")
            return
        self.listbox.insert("end", f"{src}{os.pathsep}{dst}")
        self.fileSrcVar.set("")
        self.fileDstVar.set("")
        if self.onChange:
            self.onChange()

    def _addDir(self):
        src = self.dirSrcVar.get().strip()
        dst = self.dirDstVar.get().strip()
        if not src:
            messagebox.showwarning("Missing Source", "Please select a source directory.")
            return
        if not dst:
            messagebox.showwarning("Missing Dest", "Please enter a destination path.")
            return
        self.listbox.insert("end", f"{src}{os.pathsep}{dst}")
        self.dirSrcVar.set("")
        self.dirDstVar.set("")
        if self.onChange:
            self.onChange()

    def _remove(self):
        sel = self.listbox.curselection()
        if sel:
            self.listbox.delete(sel[0])
            if self.onChange:
                self.onChange()

    def getItems(self):
        return list(self.listbox.get(0, "end"))

    def setItems(self, items):
        self.listbox.delete(0, "end")
        for item in items:
            entry = item.replace(":", os.pathsep, 1)    # 統一轉換為平台分隔符
            self.listbox.insert("end", entry)
        if self.onChange:
            self.onChange()

# ───────────────────────────────────────────────
# 主應用程式
# ───────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(0, WINDOW_MIN_H)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._initVars()
        self._buildUI()
        self._bindTrace()
        self._updatePreview()    # 初始化後立即同步一次 preview

    # ── 變數初始化 ──────────────────────────────
    def _initVars(self):
        self.varScript     = tk.StringVar()
        self.varName       = tk.StringVar()
        self.varDistPath   = tk.StringVar()
        self.varIcon       = tk.StringVar()
        self.varOnefile    = tk.BooleanVar(value=True)
        self.varConsole    = tk.BooleanVar(value=True)
        self.varPythonMode = tk.StringVar(value="default")    # "default" | "custom"
        self.varPython     = tk.StringVar()
        self.varCleanBuild = tk.BooleanVar(value=False)
        self.varCleanSpec  = tk.BooleanVar(value=False)
        self.varStatus     = tk.StringVar(value="Ready")

    # ── UI 建構 ─────────────────────────────────
    def _buildUI(self):
        mainFrame = ttk.Frame(self, padding=PAD)
        mainFrame.pack(fill="both", expand=True)

        self._buildBasicSection(mainFrame)
        self._buildNotebook(mainFrame)
        self._buildPreview(mainFrame)
        self._buildExecSection(mainFrame)

    def _buildBasicSection(self, parent):
        frame = ttk.LabelFrame(parent, text="Basic Settings", padding=PAD)
        frame.pack(fill="x", pady=(0, PAD))
        frame.columnconfigure(1, weight=1)

        ### Script / Name / Dir / Icon 欄位 ###
        rows = [
            ("* Script (.py)",  self.varScript,   self._browseScript),
            ("  Output Name",   self.varName,     None),
            ("  Output Dir",    self.varDistPath, lambda: browseDir(self.varDistPath)),
            ("  Icon (.ico)",   self.varIcon,     lambda: browseFile(self.varIcon, [("Icon", "*.ico")])),
        ]
        for i, (label, var, cmd) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, PAD), pady=2)
            ttk.Entry(frame, textvariable=var).grid(row=i, column=1, sticky="ew", pady=2)
            if cmd:
                ttk.Button(frame, text="Browse", command=cmd, width=8).grid(
                    row=i, column=2, padx=(4, 0), pady=2)

        ### Python Interpreter 欄位（Radio + 輸入框 + Browse）###
        interpRow = len(rows)
        ttk.Label(frame, text="  Python Interpreter").grid(
            row=interpRow, column=0, sticky="w", padx=(0, PAD), pady=2)

        interpInner = ttk.Frame(frame)
        interpInner.grid(row=interpRow, column=1, sticky="ew", pady=2)
        interpInner.columnconfigure(2, weight=1)    # entry 自動撐寬

        ttk.Radiobutton(interpInner, text="Default", variable=self.varPythonMode,
                        value="default", command=self._onInterpModeChange).grid(
                            row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Radiobutton(interpInner, text="Custom",  variable=self.varPythonMode,
                        value="custom",  command=self._onInterpModeChange).grid(
                            row=0, column=1, sticky="w", padx=(0, 6))
        self.interpEntry = ttk.Entry(interpInner, textvariable=self.varPython, state="disabled")
        self.interpEntry.grid(row=0, column=2, sticky="ew")
        self.interpBrowse = ttk.Button(frame, text="Browse", width=8,
                                       command=self._browsePython, state="disabled")
        self.interpBrowse.grid(row=interpRow, column=2, padx=(4, 0), pady=2)

        ### Output Mode 欄位 ###
        modeRow = interpRow + 1
        ttk.Label(frame, text="  Output Mode").grid(
            row=modeRow, column=0, sticky="w", padx=(0, PAD), pady=(PAD, 2))
        modeInner = ttk.Frame(frame)
        modeInner.grid(row=modeRow, column=1, columnspan=2, sticky="w", pady=(PAD, 2))
        ttk.Radiobutton(modeInner, text="One File  (--onefile)",
                        variable=self.varOnefile, value=True).pack(side="left", padx=(0, PAD))
        ttk.Radiobutton(modeInner, text="One Dir   (--onedir)",
                        variable=self.varOnefile, value=False).pack(side="left")

        ### Window Mode 欄位（Reset 按鈕同行靠右）###
        winRow = modeRow + 1
        ttk.Label(frame, text="  Window Mode").grid(
            row=winRow, column=0, sticky="w", padx=(0, PAD), pady=2)
        winInner = ttk.Frame(frame)
        winInner.grid(row=winRow, column=1, sticky="w", pady=2)
        ttk.Radiobutton(winInner, text="Console   (--console)",
                        variable=self.varConsole, value=True).pack(side="left", padx=(0, PAD))
        ttk.Radiobutton(winInner, text="Windowed  (--windowed)",
                        variable=self.varConsole, value=False).pack(side="left")
        ttk.Button(frame, text="Reset All Settings", command=self._resetAll).grid(
            row=winRow, column=2, sticky="e", padx=(4, 0), pady=2)

    def _browseScript(self):
        path = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if not path:
            return
        self.varScript.set(path)
        if not self.varName.get():    # 名稱欄位空白時自動帶入檔名
            self.varName.set(os.path.splitext(os.path.basename(path))[0])
        if not self.varDistPath.get():    # 輸出目錄空白時自動帶入 script 所在目錄
            self.varDistPath.set(os.path.dirname(path))

    def _onInterpModeChange(self):
        isCustom = self.varPythonMode.get() == "custom"
        self.interpEntry.configure(state="normal" if isCustom else "disabled")
        self.interpBrowse.configure(state="normal" if isCustom else "disabled")
        if not isCustom:
            self.varPython.set("")    # 切回預設時清空自訂路徑
        self._updatePreview()

    def _browsePython(self):
        if sys.platform == "win32":
            filetypes = [("Python Executable", "python.exe")]
        else:
            filetypes = [("Python Executable", "python*"), ("All Files", "*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.varPython.set(path)

    def _resetAll(self):
        if not messagebox.askyesno("Reset", "Reset all settings to default?"):
            return
        ### Basic Settings ###
        self.varScript.set("")
        self.varName.set("")
        self.varDistPath.set("")
        self.varIcon.set("")
        self.varPythonMode.set("default")
        self.varPython.set("")
        self._onInterpModeChange()    # 統一由此函式處理 entry/browse 的 disable 狀態
        ### Mode ###
        self.varOnefile.set(True)
        self.varConsole.set(True)
        ### Data Files / Imports / Excludes ###
        self.addDataEditor.setItems([])
        self.hiddenEditor.setItems([])
        self.excludeEditor.setItems([])
        ### Advanced ###
        self.extraFlagsText.delete("1.0", "end")
        self._updatePreview()

    def _buildNotebook(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="x", pady=(0, PAD))

        ### Tab 1: Data Files ###
        t1 = ttk.Frame(nb, padding=PAD)
        nb.add(t1, text="Data Files")
        self.addDataEditor = DataFileEditor(t1, onChange=self._updatePreview)
        self.addDataEditor.pack(fill="both", expand=True)

        ### Tab 2: Imports / Excludes ###
        t2 = ttk.Frame(nb, padding=PAD)
        nb.add(t2, text="Imports / Excludes")
        t2.columnconfigure(0, weight=1)
        t2.columnconfigure(1, weight=1)

        hiddenFrame = ttk.LabelFrame(t2, text="Hidden Imports", padding=PAD)
        hiddenFrame.grid(row=0, column=0, sticky="nsew", padx=(0, PAD//2))
        self.hiddenEditor = ListEditor(hiddenFrame, onChange=self._updatePreview)
        self.hiddenEditor.pack(fill="both", expand=True)

        excludeFrame = ttk.LabelFrame(t2, text="Exclude Modules", padding=PAD)
        excludeFrame.grid(row=0, column=1, sticky="nsew", padx=(PAD//2, 0))
        self.excludeEditor = ListEditor(excludeFrame, onChange=self._updatePreview)
        self.excludeEditor.pack(fill="both", expand=True)

        ### Tab 3: Advanced ###
        t3 = ttk.Frame(nb, padding=PAD)
        nb.add(t3, text="Advanced")
        ttk.Label(t3, text="Extra flags (raw):").pack(anchor="w")
        self.extraFlagsText = tk.Text(t3, height=4, relief="solid", bd=1)
        self.extraFlagsText.pack(fill="x")
        self.extraFlagsText.bind("<KeyRelease>", lambda _: self._updatePreview())    # 按鍵放開時同步 preview
        ttk.Label(t3, text="e.g.  --clean  --noupx  --debug all",
                  foreground="#888", font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))
        ttk.Label(t3, text="注意：flags 以空白分隔，路徑中若含空格會被截斷，建議避免。",
                  foreground="#888", font=("Segoe UI", 8)).pack(anchor="w")

    def _buildPreview(self, parent):
        frame = ttk.LabelFrame(parent, text="Command Preview", padding=PAD)
        frame.pack(fill="x", pady=(0, PAD))

        ### 指令文字 + Copy 按鈕 ###
        topRow = ttk.Frame(frame)
        topRow.pack(fill="x")

        self.previewText = tk.Text(topRow, height=1, wrap="none",
                                   font=("Consolas", 9), relief="solid", bd=1,
                                   state="disabled", bg="white")
        self.previewText.pack(side="left", fill="x", expand=True)
        ttk.Button(topRow, text="Copy", width=6, command=self._copyPreview).pack(side="left", padx=(4, 0))

        ### 橫向捲軸（指令過長時可滑動檢視）###
        scrollX = ttk.Scrollbar(frame, orient="horizontal", command=self.previewText.xview)
        self.previewText.configure(xscrollcommand=scrollX.set)
        scrollX.pack(fill="x")

    def _copyPreview(self):
        self.clipboard_clear()
        self.clipboard_append(self.previewText.get("1.0", "end").strip())
        self.varStatus.set("Command copied to clipboard.")

    def _buildExecSection(self, parent):
        frame = ttk.LabelFrame(parent, text="Build", padding=PAD)
        frame.pack(fill="both", expand=True)

        ### 控制列 ###
        ctrlRow = ttk.Frame(frame)
        ctrlRow.pack(fill="x", pady=(0, PAD//2))

        self.btnBuild = ttk.Button(ctrlRow, text="▶  Build", command=self._runBuild)
        self.btnBuild.pack(side="left")

        ttk.Separator(ctrlRow, orient="vertical").pack(side="left", fill="y", padx=PAD)

        ttk.Checkbutton(ctrlRow, text="Delete build/ after success",
                        variable=self.varCleanBuild).pack(side="left")
        ttk.Checkbutton(ctrlRow, text="Delete .spec after success",
                        variable=self.varCleanSpec).pack(side="left", padx=(4, 0))

        ttk.Separator(ctrlRow, orient="vertical").pack(side="left", fill="y", padx=PAD)

        ttk.Button(ctrlRow, text="Import .spec",
                   command=self._importSpec).pack(side="left", padx=(0, 4))
        ttk.Button(ctrlRow, text="Export .spec",
                   command=self._exportSpec).pack(side="left")

        self.btnOpenFolder = ttk.Button(ctrlRow, text="Open Output Folder",
                                        command=self._openOutput, state="disabled")
        self.btnOpenFolder.pack(side="right")

        ### Log 工具列（清空按鈕）###
        logToolbar = ttk.Frame(frame)
        logToolbar.pack(fill="x", pady=(0, 2))
        self.btnClearLog = ttk.Button(logToolbar, text="Clear Log", width=10,
                                      command=self._logClear)
        self.btnClearLog.pack(side="right")

        ### Log 輸出區 ###
        logFrame = ttk.Frame(frame)
        logFrame.pack(fill="both", expand=True)

        self.logText = tk.Text(logFrame, bg=LOG_BG, fg=LOG_FG, wrap="none",
                               font=("Consolas", 9), relief="flat", state="disabled")
        scrollY = ttk.Scrollbar(logFrame, orient="vertical",   command=self.logText.yview)
        scrollX = ttk.Scrollbar(logFrame, orient="horizontal", command=self.logText.xview)
        self.logText.configure(yscrollcommand=scrollY.set, xscrollcommand=scrollX.set)

        self.logText.tag_config("err", foreground=LOG_ERR)
        self.logText.tag_config("ok",  foreground=LOG_OK)

        scrollY.pack(side="right",  fill="y")
        scrollX.pack(side="bottom", fill="x")
        self.logText.pack(fill="both", expand=True)

        ### 狀態列 ###
        statusBar = ttk.Frame(parent)
        statusBar.pack(fill="x", side="bottom")
        ttk.Separator(statusBar).pack(fill="x")
        ttk.Label(statusBar, textvariable=self.varStatus,
                  anchor="w", padding=(4, 2)).pack(fill="x")

    # ── Trace / Preview ────────────────────────
    def _bindTrace(self):
        for var in (self.varScript, self.varName, self.varDistPath,
                    self.varIcon, self.varOnefile, self.varConsole,
                    self.varPython, self.varPythonMode):
            var.trace_add("write", lambda *_: self._updatePreview())

    def _buildCommand(self):
        python   = self.varPython.get().strip() if self.varPythonMode.get() == "custom" else ""
        parts    = [python, "-m", "PyInstaller"] if python else ["pyinstaller"]
        name     = self.varName.get().strip()
        distPath = self.varDistPath.get().strip()
        script   = self.varScript.get().strip()

        # Output Name 空白時，以 script 檔名作為 fallback（與 PyInstaller 預設一致）
        effectiveName = name or (os.path.splitext(os.path.basename(script))[0] if script else "")

        if self.varOnefile.get():
            parts.append("--onefile")
        else:
            parts.append("--onedir")

        if self.varConsole.get():
            parts.append("--console")
        else:
            parts.append("--windowed")

        if name:
            parts += ["--name", name]

        if distPath:
            parts += ["--distpath", distPath]

        icon = self.varIcon.get().strip()
        if icon:
            parts += ["--icon", icon]

        for entry in self.addDataEditor.getItems():
            parts += ["--add-data", entry]    # entry 已使用平台分隔符

        for hi in self.hiddenEditor.getItems():
            parts += ["--hidden-import", hi]

        for ex in self.excludeEditor.getItems():
            parts += ["--exclude-module", ex]

        extra = self.extraFlagsText.get("1.0", "end").strip()
        if extra:
            parts += extra.split()

        if script:
            absDistPath  = os.path.abspath(distPath or "dist")
            outputFolder = os.path.join(absDistPath, f"{effectiveName}_Output") if effectiveName else absDistPath
            parts += ["--specpath", outputFolder]
            parts += ["--workpath",  os.path.join(outputFolder, "build")]
            parts.append(script)

        return parts

    def _updatePreview(self):
        cmd = " ".join(self._buildCommand())
        self.previewText.configure(state="normal")
        self.previewText.delete("1.0", "end")
        self.previewText.insert("1.0", cmd)
        self.previewText.configure(state="disabled")

    # ── Log 輔助方法 ────────────────────────────
    def _logWrite(self, text, tag=None):
        self.logText.configure(state="normal")
        self.logText.insert("end", text, tag or "")
        self.logText.configure(state="disabled")

    def _logClear(self):
        self.logText.configure(state="normal")
        self.logText.delete("1.0", "end")
        self.logText.configure(state="disabled")

    def _logScroll(self):
        self.logText.see("end")

    # ── Build 流程 ──────────────────────────────
    def _runBuild(self):
        script = self.varScript.get().strip()
        if not script:
            messagebox.showwarning("Missing Script", "Please select a Python script first.")
            return

        # 預先計算 outputFolder，供 _buildCommand 的 --specpath / --workpath 使用
        name          = self.varName.get().strip()
        script        = self.varScript.get().strip()
        distPath      = os.path.abspath(self.varDistPath.get().strip() or "dist")
        effectiveName = name or os.path.splitext(os.path.basename(script))[0]    # 與 _buildCommand 保持一致
        self._outputFolder = os.path.join(distPath, f"{effectiveName}_Output") if effectiveName else distPath
        os.makedirs(self._outputFolder, exist_ok=True)

        self._logClear()
        self._logWrite("[*] Start building...\n", "ok")
        self.after(0, self._logScroll)
        self.btnBuild.configure(state="disabled")
        self.btnOpenFolder.configure(state="disabled")
        self.btnClearLog.configure(state="disabled")
        self.varStatus.set("Building...")

        cmd = self._buildCommand()

        def worker():
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for line in proc.stdout:
                    self.after(0, self._logWrite, line)
                    self.after(0, self._logScroll)

                proc.wait()
                success = proc.returncode == 0

                if success:
                    self.after(0, self._onBuildSuccess)
                else:
                    self.after(0, self._onBuildFail)
            except FileNotFoundError:
                self.after(0, self._logWrite,
                           "[-] ERROR: 'pyinstaller' not found. Is it installed?\n", "err")
                self.after(0, self._onBuildFail,
                           "找不到 'pyinstaller' 指令。\n請確認已安裝 PyInstaller，或指定正確的 Python Interpreter。")

        threading.Thread(target=worker, daemon=True).start()

    def _onBuildSuccess(self):
        name         = self.varName.get().strip()
        script       = self.varScript.get().strip()
        distPath     = os.path.abspath(self.varDistPath.get().strip() or "dist")
        outputFolder = self._outputFolder
        effectiveName = name or os.path.splitext(os.path.basename(script))[0]    # 與 _runBuild 保持一致

        ### 將產出物從 dist/ 移入 _Output/ ###
        try:
            onefile      = self.varOnefile.get()
            isWin        = sys.platform == "win32"
            artifactName = f"{effectiveName}.exe" if (onefile and isWin) else effectiveName    # non-Windows onefile 無副檔名
            artifactSrc  = os.path.join(distPath, artifactName)

            if os.path.exists(artifactSrc):
                artifactDst = os.path.join(outputFolder, artifactName)
                if os.path.exists(artifactDst):
                    shutil.rmtree(artifactDst) if os.path.isdir(artifactDst) else os.remove(artifactDst)
                os.rename(artifactSrc, artifactDst)
                self._logWrite(f"[+] Output packaged --> {outputFolder}\n", "ok")
            else:
                self._logWrite(f"[!] Warning: expected artifact not found: {artifactSrc}\n", "err")
                messagebox.showwarning("找不到產出物",
                                       f"Build 成功但找不到預期的產出物：\n{artifactSrc}")
        except Exception as e:
            self._logWrite(f"[!] Warning: could not package output: {e}\n", "err")
            messagebox.showwarning("封裝失敗", f"無法將產出物移入輸出目錄：\n{e}")

        ### 選擇性刪除 _Output/build/ ###
        if self.varCleanBuild.get():
            buildDir = os.path.join(outputFolder, "build")
            if os.path.isdir(buildDir):
                try:
                    shutil.rmtree(buildDir)
                    self._logWrite("[*] build/ deleted.\n", "ok")
                except Exception as e:
                    self._logWrite(f"[!] Warning: could not delete build/: {e}\n", "err")
                    messagebox.showwarning("刪除失敗", f"無法刪除 build/ 目錄：\n{e}")

        ### 選擇性刪除 _Output/*.spec ###
        if self.varCleanSpec.get():
            specFile = os.path.join(outputFolder, f"{effectiveName}.spec")
            if os.path.isfile(specFile):
                try:
                    os.remove(specFile)
                    self._logWrite("[*] .spec deleted.\n", "ok")
                except Exception as e:
                    self._logWrite(f"[!] Warning: could not delete .spec: {e}\n", "err")
                    messagebox.showwarning("刪除失敗", f"無法刪除 .spec 檔案：\n{e}")

        self._logWrite("\n[+] Build succeeded.\n", "ok")
        self._logScroll()
        self.varStatus.set("[+] Build succeeded")
        self.btnBuild.configure(state="normal")
        self.btnOpenFolder.configure(state="normal")
        self.btnClearLog.configure(state="normal")
        messagebox.showinfo("Build Succeeded",
                            f"Build completed successfully.\n\nOutput folder:\n{outputFolder}")

    def _onBuildFail(self, customMsg=None):
        self._logScroll()
        self.varStatus.set("[-] Build failed -- see log for details")
        self.btnBuild.configure(state="normal")
        self.btnClearLog.configure(state="normal")

        if customMsg:
            # 特定錯誤（如找不到 pyinstaller）直接顯示說明
            messagebox.showerror("Build Failed", customMsg)
        else:
            # 一般 build 失敗：取 log 最後幾行做為錯誤摘要
            logContent = self.logText.get("1.0", "end").strip()
            lastLines  = "\n".join(logContent.splitlines()[-6:])
            messagebox.showerror("Build Failed",
                                 f"Build failed. See the log for details.\n\n--- Last output ---\n{lastLines}")

    def _openOutput(self):
        target = getattr(self, "_outputFolder", None) or self.varDistPath.get().strip() or "dist"
        openFolder(target)

    # ── Spec 匯入 / 匯出 ────────────────────────
    def _importSpec(self):
        path = filedialog.askopenfilename(filetypes=[("Spec File", "*.spec")])
        if not path:
            return

        data = parseSpec(path)
        self.varName.set(data["name"])
        self.varDistPath.set(data["distpath"])
        self.varIcon.set(data["icon"])
        self.varOnefile.set(data["onefile"])
        self.varConsole.set(data["console"])
        self.addDataEditor.setItems(data["addData"])    # setItems 內部統一轉換分隔符
        self.hiddenEditor.setItems(data["hiddenImports"])
        self.excludeEditor.setItems(data["excludes"])
        self.extraFlagsText.delete("1.0", "end")
        if data["extraFlags"]:
            self.extraFlagsText.insert("1.0", data["extraFlags"])

        self._updatePreview()    # extraFlagsText 不走 trace，需手動同步
        messagebox.showinfo("Import", f"Loaded: {os.path.basename(path)}")

    def _exportSpec(self):
        script = self.varScript.get().strip()
        if not script:
            messagebox.showwarning("Missing Script", "Please select a Python script first.")
            return

        savePath = filedialog.asksaveasfilename(
            defaultextension=".spec",
            filetypes=[("Spec File", "*.spec")],
            initialfile=self.varName.get() or "output"
        )
        if not savePath:
            return

        name      = self.varName.get().strip() or os.path.splitext(os.path.basename(script))[0]
        distPath  = self.varDistPath.get().strip() or "dist"
        icon      = self.varIcon.get().strip()
        iconStr   = f"['{icon}']" if icon else "[]"
        onefile   = self.varOnefile.get()
        console   = self.varConsole.get()

        addDataList = [f"('{e.split(os.pathsep)[0]}', '{e.split(os.pathsep)[1]}')"
                       for e in self.addDataEditor.getItems() if os.pathsep in e]
        hiddenList  = [f"'{h}'" for h in self.hiddenEditor.getItems()]
        excludeList = [f"'{e}'" for e in self.excludeEditor.getItems()]

        if onefile:
            specContent = f"""\
# -*- mode: python ; coding: utf-8 -*-
# Generated by PyInstaller GUI

a = Analysis(
    ['{script}'],
    pathex=[],
    binaries=[],
    datas=[{', '.join(addDataList)}],
    hiddenimports=[{', '.join(hiddenList)}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{', '.join(excludeList)}],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='{name}',
    icon={iconStr},
    console={console},
    bootloader_ignore_signals=False,
)
"""
        else:
            specContent = f"""\
# -*- mode: python ; coding: utf-8 -*-
# Generated by PyInstaller GUI

a = Analysis(
    ['{script}'],
    pathex=[],
    binaries=[],
    datas=[{', '.join(addDataList)}],
    hiddenimports=[{', '.join(hiddenList)}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{', '.join(excludeList)}],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    name='{name}',
    icon={iconStr},
    console={console},
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='{name}',
)
"""

        try:
            with open(savePath, "w", encoding="utf-8") as f:
                f.write(specContent)
            messagebox.showinfo("Export", f"Saved: {os.path.basename(savePath)}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


# ───────────────────────────────────────────────
# 程式進入點
# ───────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()