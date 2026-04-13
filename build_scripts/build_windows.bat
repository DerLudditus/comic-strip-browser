@echo off
REM Build Comic Strip Browser for Windows (PyInstaller onedir)
REM Assumes: dependencies already installed in your environment
REM Run from the project root directory

setlocal

echo === Comic Strip Browser — Windows Build ===

if not exist "comic_browser_onedir.spec" (
    echo ✗ comic_browser_onedir.spec not found
    exit /b 1
)

if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

python -m PyInstaller comic_browser_onedir.spec --clean --noconfirm

if exist "dist\ComicStripBrowser\ComicStripBrowser.exe" (
    echo ✓ dist\ComicStripBrowser\
) else (
    echo ✗ Build failed
    exit /b 1
)

endlocal
