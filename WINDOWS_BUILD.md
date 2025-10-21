# Building for Windows using cx_Freeze

Since PyInstaller has issues with PyQt6 on Windows, we use cx_Freeze as an alternative.

## Prerequisites

1. **Python 3.8+** installed from [python.org](https://www.python.org/downloads/)
2. Make sure Python is added to PATH during installation

## Quick Build

Simply run the build script:

```cmd
build_scripts\build_windows_cxfreeze.bat
```

This will:
1. Create a virtual environment
2. Install all dependencies including cx_Freeze
3. Build the executable
4. Place the result in `build/exe.win-amd64-3.x/`

## Manual Build Process

If you prefer to build manually:

### 1. Create virtual environment

```cmd
python -m venv venv_win
venv_win\Scripts\activate.bat
```

### 2. Install dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
pip install cx_Freeze
```

### 3. Build the executable

```cmd
python setup_cxfreeze.py build
```

### 4. Find your executable

The executable will be in:
```
build\exe.win-amd64-3.x\ComicStripBrowser.exe
```

## Testing

Run the executable directly:

```cmd
build\exe.win-amd64-3.x\ComicStripBrowser.exe
```

## Distribution

### Option 1: ZIP Archive

Create a ZIP file of the entire `build\exe.win-amd64-3.x\` directory:

```cmd
cd build
tar -a -c -f ComicStripBrowser-Windows.zip exe.win-amd64-3.x
```

Users extract and run `ComicStripBrowser.exe`.

### Option 2: Installer (Recommended)

Use **Inno Setup** (free) to create a proper Windows installer:

1. Download Inno Setup from [jrsoftware.org](https://jrsoftware.org/isdl.php)
2. Create an installer script (see `installer.iss` example below)
3. Compile the installer

### Option 3: Portable EXE

For a single-file executable, you can try:

```cmd
python setup_cxfreeze.py bdist_msi
```

This creates an MSI installer in the `dist/` directory.

## Example Inno Setup Script

Create `installer.iss`:

```ini
[Setup]
AppName=Comic Strip Browser
AppVersion=1.1.0
DefaultDirName={pf}\ComicStripBrowser
DefaultGroupName=Comic Strip Browser
OutputDir=releases
OutputBaseFilename=ComicStripBrowser-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "build\exe.win-amd64-3.x\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Comic Strip Browser"; Filename: "{app}\ComicStripBrowser.exe"
Name: "{commondesktop}\Comic Strip Browser"; Filename: "{app}\ComicStripBrowser.exe"

[Run]
Filename: "{app}\ComicStripBrowser.exe"; Description: "Launch Comic Strip Browser"; Flags: postinstall nowait skipifsilent
```

## Troubleshooting

### Missing DLL errors

If users get DLL errors, they may need to install:
- [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### Qt platform plugin errors

If you get "Could not find the Qt platform plugin", make sure the `platforms` folder is included in the build. cx_Freeze should handle this automatically.

### Import errors

If specific modules aren't found, add them to the `packages` list in `setup_cxfreeze.py`.

## Why cx_Freeze instead of PyInstaller?

- Better Qt6 support on Windows
- More reliable DLL bundling
- Cleaner handling of Python packages
- Less likely to be flagged by antivirus

## Comparison with PyInstaller

| Feature | cx_Freeze | PyInstaller |
|---------|-----------|-------------|
| Qt6 Support | ✅ Excellent | ⚠️ Problematic |
| Build Speed | ⚡ Fast | 🐌 Slower |
| File Size | 📦 Moderate | 📦 Moderate |
| Ease of Use | 👍 Simple | 👍 Simple |
| Windows Support | ✅ Great | ⚠️ Issues |

## Alternative: Nuitka

If cx_Freeze also fails, try Nuitka (compiles to native code):

```cmd
pip install nuitka
python -m nuitka --standalone --windows-disable-console --enable-plugin=pyqt6 main.py
```

Nuitka is slower to build but produces highly optimized executables.
