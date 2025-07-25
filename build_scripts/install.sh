#!/bin/bash
"""
Linux installation script for Comic Strip Browser
"""

set -e

APP_NAME="Comic Strip Browser"
EXECUTABLE_NAME="comic-strip-browser"
DESKTOP_FILE="comic-strip-browser.desktop"
ICON_FILE="comic-strip-browser.png"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_status "Checking system requirements..."
    
    # Check if running on Linux
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_error "This installer is for Linux systems only."
        exit 1
    fi
    
    # Check for required directories
    if [ ! -d "$HOME/.local/bin" ]; then
        mkdir -p "$HOME/.local/bin"
        print_status "Created ~/.local/bin directory"
    fi
    
    if [ ! -d "$HOME/.local/share/applications" ]; then
        mkdir -p "$HOME/.local/share/applications"
        print_status "Created ~/.local/share/applications directory"
    fi
    
    if [ ! -d "$HOME/.local/share/icons" ]; then
        mkdir -p "$HOME/.local/share/icons"
        print_status "Created ~/.local/share/icons directory"
    fi
}

install_executable() {
    print_status "Installing executable..."
    
    # Find the executable
    if [ -f "./$EXECUTABLE_NAME" ]; then
        EXECUTABLE_PATH="./$EXECUTABLE_NAME"
    else
        print_error "Executable '$EXECUTABLE_NAME' not found!"
        print_error "Make sure you've built the application first with: python build_scripts/build.py"
        exit 1
    fi
    
    # Copy executable to user's local bin
    cp "$EXECUTABLE_PATH" "$HOME/.local/bin/$EXECUTABLE_NAME"
    chmod +x "$HOME/.local/bin/$EXECUTABLE_NAME"
    
    print_status "Executable installed to ~/.local/bin/$EXECUTABLE_NAME"
}

install_desktop_file() {
    print_status "Installing desktop integration..."
    
    # Create the desktop file   

    print_status "Creating a desktop file for a locally installed binary..."
        
        # Create basic desktop file
        cat > "/tmp/$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Browse a selection of comic strips from GoComics.com
Exec=$HOME/.local/bin/$EXECUTABLE_NAME
Icon=comic-strip-browser
Terminal=false
Categories=Graphics;Viewer;
Keywords=comic;comics;strips;gocomics;entertainment;
StartupNotify=true
EOF
    DESKTOP_PATH="/tmp/$DESKTOP_FILE"  
    
    # Install desktop file
    cp "$DESKTOP_PATH" "$HOME/.local/share/applications/$DESKTOP_FILE"
    
    print_status "Desktop file installed to ~/.local/share/applications/$DESKTOP_FILE"
}

install_icon() {
    print_status "Installing application icon..."
    
    # Find icon file
    if [ -f "./$ICON_FILE" ]; then
        cp "./$ICON_FILE" "$HOME/.local/share/icons/$ICON_FILE"
        print_status "Icon installed to ~/.local/share/icons/$ICON_FILE"
    else
        print_warning "Icon file not found, application will use default icon"
    fi
}

update_desktop_database() {
    print_status "Updating desktop database..."
    
    # Update desktop database if update-desktop-database is available
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
        print_status "Desktop database updated"
    else
        print_warning "update-desktop-database not found, desktop integration may require logout/login"
    fi
}

create_uninstaller() {
    print_status "Creating uninstaller..."
    
    cat > "$HOME/.local/bin/uninstall-comic-strip-browser" << 'EOF'
#!/bin/bash
# Uninstaller for Comic Strip Browser

echo "Uninstalling Comic Strip Browser..."

# Remove executable
rm -f $HOME/.local/bin/comic-strip-browser

# Remove desktop file
rm -f $HOME/.local/share/applications/comic-strip-browser.desktop

# Remove icon
rm -f $HOME/.local/share/icons/comic-strip-browser.png

# Remove this uninstaller
rm -f $HOME/.local/bin/uninstall-comic-strip-browser

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "Comic Strip Browser has been uninstalled."
EOF
    
    chmod +x "$HOME/.local/bin/uninstall-comic-strip-browser"
    print_status "Uninstaller created at ~/.local/bin/uninstall-comic-strip-browser"
}

main() {
    echo "============================================"
    echo "  Comic Strip Browser - Linux Installer"
    echo "============================================"
    echo
    
    check_requirements
    install_executable
    install_desktop_file
    install_icon
    update_desktop_database
    create_uninstaller
    
    echo
    print_status "Installation completed successfully!"
    echo
    echo "You can now:"
    echo "  • Run from terminal: $EXECUTABLE_NAME"
    echo "  • Find in applications menu: $APP_NAME"
    echo "  • Uninstall with: uninstall-comic-strip-browser"
    echo
    
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        print_warning "~/.local/bin is not in your PATH"
        print_warning "Add this line to your ~/.bashrc or ~/.profile:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        print_warning "Then restart your terminal or run: source ~/.bashrc"
    fi
}

# Run main function
main "$@"
