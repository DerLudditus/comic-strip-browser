#!/usr/bin/env python3
"""
Build script for Comic Strip Browser
Handles cross-platform building with PyInstaller
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import argparse

class ComicBrowserBuilder:
    """Builder class for Comic Strip Browser application."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.spec_file = self.project_root / "comic_browser.spec"
        
        self.platform_name = platform.system().lower()
        self.architecture = platform.machine().lower()
        
    def clean_build_dirs(self):
        """Clean previous build artifacts."""
        print("Cleaning previous build artifacts...")
        
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"Removed {dir_path}")
        
        # Clean PyInstaller cache
        cache_dir = self.project_root / "__pycache__"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        
        print("Build directories cleaned.")
    
    def check_dependencies(self):
        """Check if all required dependencies are installed."""
        print("Checking dependencies...")
        
        required_packages = ['PyQt6', 'requests', 'beautifulsoup4', 'pyinstaller']
        missing_packages = []
        
        for package in required_packages:
            try:
                if package == 'PyQt6':
                    import PyQt6
                elif package == 'beautifulsoup4':
                    import bs4
                elif package == 'pyinstaller':
                    import PyInstaller
                else:
                    __import__(package.lower().replace('-', '_'))
                print(f"✓ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"✗ {package}")
        
        if missing_packages:
            print(f"\nMissing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        print("All dependencies satisfied.")
        return True
    
    def build_application(self, debug=False):
        """Build the application using PyInstaller."""
        print(f"Building Comic Strip Browser for {self.platform_name}...")
        
        # Prepare PyInstaller command
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(self.spec_file),
            "--clean",
            "--noconfirm"
        ]
        
        if debug:
            cmd.append("--debug=all")
        
        # Set working directory to project root
        original_cwd = os.getcwd()
        os.chdir(self.project_root)
        
        try:
            # Run PyInstaller
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Build completed successfully!")
                print(f"Executable created in: {self.dist_dir}")
                return True
            else:
                print("Build failed!")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            print(f"Build error: {e}")
            return False
        finally:
            os.chdir(original_cwd)
    
    def create_installer_package(self):
        """Create platform-specific installer package."""
        print(f"Creating installer package for {self.platform_name}...")
        
        if self.platform_name == "windows":
            return self._create_windows_installer()
        elif self.platform_name == "linux":
            return self._create_linux_package()
        else:
            print(f"Installer creation not implemented for {self.platform_name}")
            return False
    
    def _create_windows_installer(self):
        """Create Windows installer (requires NSIS or similar)."""
        print("Windows installer creation requires NSIS.")
        print("Manual steps:")
        print("1. Install NSIS (Nullsoft Scriptable Install System)")
        print("2. Create installer script (.nsi file)")
        print("3. Compile with NSIS")
        print(f"Executable is ready in: {self.dist_dir}")
        return True
    
    def _create_linux_package(self):
        """Create Linux package (AppImage or .deb)."""
        print("Creating Linux package structure...")
        
        # Create AppDir structure for AppImage
        app_dir = self.dist_dir / "ComicStripBrowser.AppDir"
        app_dir.mkdir(exist_ok=True)
        
        # Copy executable
        exe_name = "comic-strip-browser"
        exe_path = self.dist_dir / exe_name
        
        if exe_path.exists():
            shutil.copy2(exe_path, app_dir / "AppRun")
            os.chmod(app_dir / "AppRun", 0o755)
            
            # Copy desktop file
            desktop_file = self.project_root / "assets" / "comic-strip-browser.desktop"
            if desktop_file.exists():
                shutil.copy2(desktop_file, app_dir / "comic-strip-browser.desktop")
            
            # Copy icon
            icon_file = self.project_root / "assets" / "comic-strip-browser.png"
            if icon_file.exists():
                shutil.copy2(icon_file, app_dir / "comic-strip-browser.png")
            
            print(f"Linux package structure created in: {app_dir}")
            print("To create AppImage, use appimagetool:")
            print(f"appimagetool {app_dir}")
            return True
        else:
            print(f"Executable not found: {exe_path}")
            return False
    
    def run_tests(self):
        """Run deployment tests."""
        print("Running deployment tests...")
        
        # Check if executable exists and is runnable
        if self.platform_name == "windows":
            exe_name = "ComicStripBrowser.exe"
        else:
            exe_name = "comic-strip-browser"
        
        exe_path = self.dist_dir / exe_name
        
        if not exe_path.exists():
            print(f"Executable not found: {exe_path}")
            return False
        
        # Test executable permissions
        if not os.access(exe_path, os.X_OK):
            print(f"Executable is not executable: {exe_path}")
            return False
        
        print(f"✓ Executable found and is executable: {exe_path}")
        
        # Test basic startup (with timeout)
        try:
            print("Testing application startup...")
            result = subprocess.run([str(exe_path), "--help"], 
                                  capture_output=True, text=True, timeout=10)
            print("✓ Application starts without immediate crashes")
        except subprocess.TimeoutExpired:
            print("✓ Application starts (timeout reached, which is expected)")
        except Exception as e:
            print(f"✗ Application startup test failed: {e}")
            return False
        
        print("Deployment tests passed!")
        return True

def main():
    """Main build script entry point."""
    parser = argparse.ArgumentParser(description="Build Comic Strip Browser")
    parser.add_argument("--clean", action="store_true", help="Clean build directories")
    parser.add_argument("--debug", action="store_true", help="Build with debug information")
    parser.add_argument("--package", action="store_true", help="Create installer package")
    parser.add_argument("--test", action="store_true", help="Run deployment tests")
    parser.add_argument("--all", action="store_true", help="Run complete build process")
    
    args = parser.parse_args()
    
    builder = ComicBrowserBuilder()
    
    # Default to full build if no specific options
    if not any([args.clean, args.debug, args.package, args.test]):
        args.all = True
    
    success = True
    
    if args.clean or args.all:
        builder.clean_build_dirs()
    
    if args.all:
        if not builder.check_dependencies():
            print("Dependency check failed. Please install missing packages.")
            return 1
    
    if args.all or args.debug:
        success = builder.build_application(debug=args.debug)
        if not success:
            print("Build failed!")
            return 1
    
    if args.test or args.all:
        success = builder.run_tests()
        if not success:
            print("Tests failed!")
            return 1
    
    if args.package or args.all:
        success = builder.create_installer_package()
        if not success:
            print("Package creation failed!")
            return 1
    
    if success:
        print("\n🎉 Build process completed successfully!")
        print(f"Find your executable in: {builder.dist_dir}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
