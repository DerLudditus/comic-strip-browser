#!/bin/bash
# Linux build script for Comic Strip Browser
# This script handles virtual environment setup and building

set -e  # Exit on any error

echo "Building Comic Strip Browser for Linux..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher using your package manager"
    echo "Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "Fedora: sudo dnf install python3 python3-pip"
    echo "Arch: sudo pacman -S python python-pip"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        echo "Make sure you have python3-venv installed:"
        echo "Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install requirements"
    echo "This might be due to system-wide Python packages conflict"
    echo "Please see DEPLOYMENT.md for troubleshooting"
    exit 1
fi

# Run the build
echo "Running build process..."
python build_scripts/build.py --all
if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo ""
echo "Build completed successfully!"
echo "Executable is available in: dist/comic-strip-browser"
echo "AppDir structure is available in: dist/ComicStripBrowser.AppDir"
echo ""
