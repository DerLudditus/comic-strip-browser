@echo off
REM Build script for Comic Strip Browser on Windows
REM Run this from the project root directory

echo Building Comic Strip Browser for Windows...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build the application
echo Building application with PyInstaller...
python -m PyInstaller comic_browser.spec --clean --noconfirm

REM Check if build was successful
if exist "dist\ComicStripBrowser.exe" (
    echo.
    echo ✓ Build completed successfully!
    echo Executable created: dist\ComicStripBrowser.exe
    echo.
    
    REM Test the executable
    echo Testing executable...
    timeout /t 2 >nul
    start /wait dist\ComicStripBrowser.exe --help
    
    echo.
    echo Build process completed!
    echo You can now create an installer using NSIS or distribute the dist folder.
) else (
    echo.
    echo ✗ Build failed!
    echo Check the output above for errors.
)

pause