import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import re

# ───────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────
WINDOW_TITLE  = "PyInstaller GUI"
WINDOW_W      = 810
WINDOW_H      = 870
WINDOW_MIN_H  = 830
PAD           = 8
BG            = "#F5F5F5"
ACCENT        = "#2A6EBB"
LOG_BG        = "#1E1E1E"
LOG_FG        = "#D4D4D4"
LOG_ERR       = "#F44747"
LOG_OK        = "#6A9955"

# ───────────────────────────────────────────────
# Helpers
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
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

# ───────────────────────────────────────────────
# Spec Parser
# ───────────────────────────────────────────────
def parseSpec(specPath):
    """Parse a .spec file and return a dict of extracted values."""
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
        messagebox.showerror("Spec Parse Error", str(e))

    return result

# ───────────────────────────────────────────────
# List Editor Widget (for imports / excludes)
# ───────────────────────────────────────────────
class ListEditor(ttk.Frame):
    """Manages a simple list of string entries with optional change callback."""
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
# Data File Editor Widget (src + dst, file or dir)
# ───────────────────────────────────────────────
class DataFileEditor(ttk.Frame):
    """Two-panel widget: one for adding files, one for adding dirs, shared result list."""
    def __init__(self, parent, onChange=None, **kw):
        super().__init__(parent, **kw)
        self.onChange = onChange
        self._buildUI()

    def _buildUI(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        ### Add File panel ###
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

        ### Add Dir panel ###
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

        ### Shared result list ###
        listFrame = ttk.LabelFrame(self, text="Entries  (src → dest)", padding=PAD)
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
            if not self.fileDstVar.get():    # auto-fill dst with filename's folder if empty
                self.fileDstVar.set(".")

    def _browseDirSrc(self):
        path = filedialog.askdirectory()
        if path:
            self.dirSrcVar.set(path)
            if not self.dirDstVar.get():
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
            # normalise stored src:dst → platform separator
            entry = item.replace(":", os.pathsep, 1)
            self.listbox.insert("end", entry)
        if self.onChange:
            self.onChange()

# ───────────────────────────────────────────────
# Main App
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

    # ── Variables ──────────────────────────────
    def _initVars(self):
        self.varScript    = tk.StringVar()
        self.varName      = tk.StringVar()
        self.varDistPath  = tk.StringVar()
        self.varIcon      = tk.StringVar()
        self.varOnefile   = tk.BooleanVar(value=True)
        self.varConsole   = tk.BooleanVar(value=False)
        self.varPythonMode = tk.StringVar(value="default")    # "default" | "custom"
        self.varPython     = tk.StringVar()
        self.varCleanBuild = tk.BooleanVar(value=False)
        self.varCleanSpec  = tk.BooleanVar(value=False)
        self.varStatus     = tk.StringVar(value="Ready")

    # ── UI ─────────────────────────────────────
    def _buildUI(self):
        mainFrame = ttk.Frame(self, padding=PAD)
        mainFrame.pack(fill="both", expand=True)

        self._buildBasicSection(mainFrame)
        self._buildModeSection(mainFrame)
        self._buildNotebook(mainFrame)
        self._buildPreview(mainFrame)
        self._buildExecSection(mainFrame)

    def _buildBasicSection(self, parent):
        frame = ttk.LabelFrame(parent, text="Basic Settings", padding=PAD)
        frame.pack(fill="x", pady=(0, PAD))
        frame.columnconfigure(1, weight=1)

        ### Script / Name / Dir / Icon rows ###
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

        ### Python Interpreter row (radio + entry + browse) ###
        interpRow = len(rows)
        ttk.Label(frame, text="  Python Interpreter").grid(
            row=interpRow, column=0, sticky="w", padx=(0, PAD), pady=2)

        interpInner = ttk.Frame(frame)
        interpInner.grid(row=interpRow, column=1, columnspan=2, sticky="ew", pady=2)
        interpInner.columnconfigure(2, weight=1)    # entry expands

        ttk.Radiobutton(interpInner, text="Default", variable=self.varPythonMode,
                        value="default", command=self._onInterpModeChange).grid(
                            row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Radiobutton(interpInner, text="Custom",  variable=self.varPythonMode,
                        value="custom",  command=self._onInterpModeChange).grid(
                            row=0, column=1, sticky="w", padx=(0, 6))
        self.interpEntry = ttk.Entry(interpInner, textvariable=self.varPython, state="disabled")
        self.interpEntry.grid(row=0, column=2, sticky="ew", padx=(0, 4))
        self.interpBrowse = ttk.Button(interpInner, text="Browse", width=8,
                                       command=self._browsePython, state="disabled")
        self.interpBrowse.grid(row=0, column=3)

        ### Reset button ###
        resetRow = interpRow + 1
        ttk.Button(frame, text="Reset All Settings", command=self._resetAll).grid(
            row=resetRow, column=0, columnspan=3, sticky="e", pady=(PAD, 0))

    def _buildModeSection(self, parent):
        frame = ttk.LabelFrame(parent, text="Mode", padding=PAD)
        frame.pack(fill="x", pady=(0, PAD))

        # Output Mode
        ttk.Label(frame, text="Output Mode", width=14, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, PAD), pady=2)
        ttk.Radiobutton(frame, text="One File  (--onefile)",
                        variable=self.varOnefile, value=True).grid(row=0, column=1, sticky="w", padx=(0, PAD))
        ttk.Radiobutton(frame, text="One Dir   (--onedir)",
                        variable=self.varOnefile, value=False).grid(row=0, column=2, sticky="w")

        # Window Mode
        ttk.Label(frame, text="Window Mode", width=14, anchor="w").grid(
            row=1, column=0, sticky="w", padx=(0, PAD), pady=2)
        ttk.Radiobutton(frame, text="Windowed  (--windowed)",
                        variable=self.varConsole, value=False).grid(row=1, column=1, sticky="w", padx=(0, PAD))
        ttk.Radiobutton(frame, text="Console   (--console)",
                        variable=self.varConsole, value=True).grid(row=1, column=2, sticky="w")

    def _browseScript(self):
        path = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if not path:
            return
        self.varScript.set(path)
        if not self.varName.get():                                  # auto-fill name if empty
            self.varName.set(os.path.splitext(os.path.basename(path))[0])
        if not self.varDistPath.get():                              # auto-fill output dir if empty
            self.varDistPath.set(os.path.dirname(path))

    def _onInterpModeChange(self):
        isCustom = self.varPythonMode.get() == "custom"
        self.interpEntry.configure(state="normal" if isCustom else "disabled")
        self.interpBrowse.configure(state="normal" if isCustom else "disabled")
        if not isCustom:
            self.varPython.set("")    # 切回預設時清空路徑
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
        self.interpEntry.configure(state="disabled")
        self.interpBrowse.configure(state="disabled")
        ### Mode ###
        self.varOnefile.set(True)
        self.varConsole.set(False)
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
        t2 = ttk.Frame(nb, padding=PAD)
        nb.add(t2, text="Data Files")
        self.addDataEditor = DataFileEditor(t2, onChange=self._updatePreview)
        self.addDataEditor.pack(fill="both", expand=True)

        ### Tab 2: Imports ###
        t3 = ttk.Frame(nb, padding=PAD)
        nb.add(t3, text="Imports / Excludes")
        t3.columnconfigure(0, weight=1)
        t3.columnconfigure(1, weight=1)

        hiddenFrame = ttk.LabelFrame(t3, text="Hidden Imports", padding=PAD)
        hiddenFrame.grid(row=0, column=0, sticky="nsew", padx=(0, PAD//2))
        self.hiddenEditor = ListEditor(hiddenFrame, onChange=self._updatePreview)
        self.hiddenEditor.pack(fill="both", expand=True)

        excludeFrame = ttk.LabelFrame(t3, text="Exclude Modules", padding=PAD)
        excludeFrame.grid(row=0, column=1, sticky="nsew", padx=(PAD//2, 0))
        self.excludeEditor = ListEditor(excludeFrame, onChange=self._updatePreview)
        self.excludeEditor.pack(fill="both", expand=True)

        ### Tab 3: Advanced ###
        t4 = ttk.Frame(nb, padding=PAD)
        nb.add(t4, text="Advanced")
        ttk.Label(t4, text="Extra flags (raw):").pack(anchor="w")
        self.extraFlagsText = tk.Text(t4, height=4, relief="solid", bd=1)
        self.extraFlagsText.pack(fill="x")
        self.extraFlagsText.bind("<KeyRelease>", lambda _: self._updatePreview())    # sync preview on keystroke
        ttk.Label(t4, text="e.g.  --clean  --noupx  --debug all",
                  foreground="#888", font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

    def _buildPreview(self, parent):
        frame = ttk.LabelFrame(parent, text="Command Preview", padding=PAD)
        frame.pack(fill="x", pady=(0, PAD))

        ### Text + copy button row ###
        topRow = ttk.Frame(frame)
        topRow.pack(fill="x")

        self.previewText = tk.Text(topRow, height=1, wrap="none",
                                   font=("Consolas", 9), relief="solid", bd=1,
                                   state="disabled", bg="white")
        self.previewText.pack(side="left", fill="x", expand=True)
        ttk.Button(topRow, text="Copy", width=6, command=self._copyPreview).pack(side="left", padx=(4, 0))

        ### Horizontal scrollbar ###
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

        ### Control row ###
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

        ### Log toolbar (clear button) ###
        logToolbar = ttk.Frame(frame)
        logToolbar.pack(fill="x", pady=(0, 2))
        ttk.Button(logToolbar, text="Clear Log", width=10,
                   command=self._logClear).pack(side="right")

        ### Log area ###
        logFrame = ttk.Frame(frame)
        logFrame.pack(fill="both", expand=True)

        self.logText = tk.Text(logFrame, bg=LOG_BG, fg=LOG_FG, wrap="none",
                               font=("Consolas", 9), relief="flat", state="disabled")
        scrollY = ttk.Scrollbar(logFrame, orient="vertical", command=self.logText.yview)
        scrollX = ttk.Scrollbar(logFrame, orient="horizontal", command=self.logText.xview)
        self.logText.configure(yscrollcommand=scrollY.set, xscrollcommand=scrollX.set)

        self.logText.tag_config("err", foreground=LOG_ERR)
        self.logText.tag_config("ok",  foreground=LOG_OK)

        scrollY.pack(side="right",  fill="y")
        scrollX.pack(side="bottom", fill="x")
        self.logText.pack(fill="both", expand=True)

        ### Status bar ###
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
        python = self.varPython.get().strip() if self.varPythonMode.get() == "custom" else ""
        parts  = [python, "-m", "PyInstaller"] if python else ["pyinstaller"]

        if self.varOnefile.get():
            parts.append("--onefile")
        else:
            parts.append("--onedir")

        if self.varConsole.get():
            parts.append("--console")
        else:
            parts.append("--windowed")

        name = self.varName.get().strip()
        if name:
            parts += ["--name", name]

        distPath = self.varDistPath.get().strip()
        if distPath:
            parts += ["--distpath", distPath]

        icon = self.varIcon.get().strip()
        if icon:
            parts += ["--icon", icon]

        for entry in self.addDataEditor.getItems():
            parts += ["--add-data", entry]    # entry already uses os.pathsep as separator

        for hi in self.hiddenEditor.getItems():
            parts += ["--hidden-import", hi]

        for ex in self.excludeEditor.getItems():
            parts += ["--exclude-module", ex]

        extra = self.extraFlagsText.get("1.0", "end").strip()
        if extra:
            parts += extra.split()

        script = self.varScript.get().strip()
        if script:
            name         = self.varName.get().strip()
            distPath     = os.path.abspath(self.varDistPath.get().strip() or "dist")
            outputFolder = os.path.join(distPath, f"{name}_Output") if name else distPath    # 永遠即時計算
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

    # ── Log helpers ────────────────────────────
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

    # ── Build ───────────────────────────────────
    def _runBuild(self):
        script = self.varScript.get().strip()
        if not script:
            messagebox.showwarning("Missing Script", "Please select a Python script first.")
            return

        # pre-compute outputFolder so _buildCommand can use it for --specpath/--workpath
        name     = self.varName.get().strip()
        distPath = os.path.abspath(self.varDistPath.get().strip() or "dist")
        self._outputFolder = os.path.join(distPath, f"{name}_Output") if name else distPath
        os.makedirs(self._outputFolder, exist_ok=True)

        self._logClear()
        self._logWrite("Start building...\n", "ok")    # always shown before log output
        self.after(0, self._logScroll)
        self.btnBuild.configure(state="disabled")
        self.btnOpenFolder.configure(state="disabled")
        self.varStatus.set("Building…")

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
                           "ERROR: 'pyinstaller' not found. Is it installed?\n", "err")
                self.after(0, self._onBuildFail)

        threading.Thread(target=worker, daemon=True).start()

    def _onBuildSuccess(self):
        import shutil
        name         = self.varName.get().strip()
        distPath     = os.path.abspath(self.varDistPath.get().strip() or "dist")
        outputFolder = self._outputFolder

        ### Move build artifact from dist/ into _Output/ ###
        try:
            onefile      = self.varOnefile.get()
            artifactName = f"{name}.exe" if onefile else name
            artifactSrc  = os.path.join(distPath, artifactName)

            if os.path.exists(artifactSrc):
                artifactDst = os.path.join(outputFolder, artifactName)
                if os.path.exists(artifactDst):
                    shutil.rmtree(artifactDst) if os.path.isdir(artifactDst) else os.remove(artifactDst)
                os.rename(artifactSrc, artifactDst)
            else:
                self._logWrite(f"Warning: expected artifact not found: {artifactSrc}\n", "err")

            self._logWrite(f"\n📦 Output packaged → {outputFolder}\n", "ok")
        except Exception as e:
            self._logWrite(f"\nWarning: could not package output: {e}\n", "err")

        ### Optionally delete _Output/build/ ###
        if self.varCleanBuild.get():
            buildDir = os.path.join(outputFolder, "build")
            if os.path.isdir(buildDir):
                try:
                    shutil.rmtree(buildDir)
                    self._logWrite("🗑  build/ deleted.\n", "ok")
                except Exception as e:
                    self._logWrite(f"Warning: could not delete build/: {e}\n", "err")

        ### Optionally delete _Output/*.spec ###
        if self.varCleanSpec.get():
            name = self.varName.get().strip()
            specFile = os.path.join(outputFolder, f"{name}.spec")
            if os.path.isfile(specFile):
                try:
                    os.remove(specFile)
                    self._logWrite("🗑  .spec deleted.\n", "ok")
                except Exception as e:
                    self._logWrite(f"Warning: could not delete .spec: {e}\n", "err")

        self._logWrite("\n✔ Build succeeded.\n", "ok")
        self._logScroll()
        self.varStatus.set("✔ Build succeeded")
        self.btnBuild.configure(state="normal")
        self.btnOpenFolder.configure(state="normal")

    def _onBuildFail(self):
        self._logScroll()
        self.varStatus.set("✘ Build failed — see log for details")
        self.btnBuild.configure(state="normal")

    def _openOutput(self):
        target = getattr(self, "_outputFolder", None) or self.varDistPath.get().strip() or "dist"
        openFolder(target)

    # ── Spec Import / Export ────────────────────
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
        self.addDataEditor.setItems(data["addData"])    # setItems normalises : → os.pathsep internally
        self.hiddenEditor.setItems(data["hiddenImports"])
        self.excludeEditor.setItems(data["excludes"])
        self.extraFlagsText.delete("1.0", "end")
        if data["extraFlags"]:
            self.extraFlagsText.insert("1.0", data["extraFlags"])

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
# Entry Point
# ───────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()