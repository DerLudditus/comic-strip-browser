@echo off
REM Build script for Comic Strip Browser using cx_Freeze
REM Alternative to PyInstaller for better Windows compatibility

echo ========================================
echo Comic Strip Browser - Windows Build
echo Using cx_Freeze
echo ========================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or later from python.org
    pause
    exit /b 1
)

echo Python found: 
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv_win" (
    echo Creating virtual environment...
    python -m venv venv_win
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv_win\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install cx_Freeze
echo Installing cx_Freeze...
pip install cx_Freeze
if %errorlevel% neq 0 (
    echo ERROR: Failed to install cx_Freeze
    pause
    exit /b 1
)

REM Clean previous build
if exist "build" (
    echo Cleaning previous build...
    rmdir /s /q build
)

REM Build the executable
echo.
echo Building executable with cx_Freeze...
python setup_cxfreeze.py build
if %errorlevel% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Find the build directory
for /d %%i in (build\exe.*) do set BUILD_DIR=%%i

if not defined BUILD_DIR (
    echo ERROR: Build directory not found!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: %BUILD_DIR%\ComicStripBrowser.exe
echo.
echo You can now:
echo 1. Test the executable: %BUILD_DIR%\ComicStripBrowser.exe
echo 2. Create a ZIP for distribution
echo 3. Create an installer using Inno Setup or NSIS
echo.

REM Deactivate virtual environment
deactivate

pause
