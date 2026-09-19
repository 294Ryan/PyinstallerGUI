<!---------------- LINKS_START -------------------->

[license]: https://github.com/294Ryan/PyinstallerGUI/blob/main/LICENSE
[readme]: https://github.com/294Ryan/PyinstallerGUI/blob/main/README.md

<!----------------- LINKS_END --------------------->

<div id="top" align='center'>
  <h1><b>Development & Contribution Guide</b></h1>
</div>

Thank you for contributing to **PyInstaller GUI**. You can help the project in the following ways:

- Submit bug reports with clear reproduction steps
- Suggest new features or optimizations (please open an issue first)
- Improve documentation
- Contribute code, UI improvements, or `.spec` parsing enhancements

---

## **Setting Up**

```
git clone https://github.com/294Ryan/PyinstallerGUI.git
cd PyinstallerGUI
```

---

## **Installing Requirements**

This project uses **Python standard library only** — no `pip install` is required to run from source.

| Name | Requirement |
| :-: | :--- |
| **Python** | 3.x |
| **PyInstaller** | Required only if you intend to run actual builds: `pip install pyinstaller` |

---

## **Technologies Used**

| Name | Description |
| :--: | :--- |
| **tkinter / ttk** | UI framework; part of Python's standard library — no external GUI dependency. |
| **subprocess** | Invokes the `pyinstaller` command and streams stdout/stderr to the log panel in real time. |
| **threading** | Runs the build process on a background thread to keep the UI responsive. |
| **shutil / os** | Handles post-build artifact relocation and optional cleanup of `build/` and `.spec`. |
| **re** | Parses `.spec` files to extract `Analysis`, `EXE`, `datas`, `hiddenimports`, and `excludes` fields. |

---

## **Project Structure**

```
PyinstallerGUI/
├── images/
│   ├── Banner.png
│   └── tk_app.png
├── .gitignore
├── icon.ico
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── tk_pyinstaller_gui.py      # Single-file application entry point
└── tk_pyinstaller_gui.spec    # .spec file
```

---

## **Notes**

- Please comply with the terms of the license during development. See [LICENSE][license].
- For usage and feature overview, refer to the [README][readme].

<br>

<div align="center">
  <a href="#top">Back to top</a>
</div>
