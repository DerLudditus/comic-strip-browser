# Building RPM Packages for Comic Strip Browser

This guide explains how to build RPM packages for Fedora, RHEL, and other RPM-based distributions.

## Prerequisites

### Install Required Tools

For Fedora:
```bash
sudo dnf -y install rpm-build rpmdevtools python3-devel python3-pip python3-virtualenv python3-PyQt6 python3-requests python3-beautifulsoup4
```

## Quick Build

Simply run the build script:

```bash
./build_scripts/build_rpm.sh
```

This will:
1. Create the RPM build environment in `~/rpmbuild`
2. Package the source code into a tarball
3. Build both binary and source RPM packages
4. Copy the resulting RPMs to the `releases/` directory

## Manual Build Process

If you prefer to build manually:

### 1. Set up RPM build environment

```bash
rpmdev-setuptree
```

This creates the directory structure at `~/rpmbuild/`:
- `BUILD/` - Build directory
- `RPMS/` - Binary RPMs
- `SOURCES/` - Source tarballs
- `SPECS/` - Spec files
- `SRPMS/` - Source RPMs

### 2. Create source tarball

```bash
VERSION=$(python3 -c "from version import __version__; print(__version__)")
tar czf ~/rpmbuild/SOURCES/comic-strip-browser-${VERSION}.tar.gz \
    --transform "s,^,comic-strip-browser-${VERSION}/," \
    main.py version.py requirements.txt comic_browser.spec \
    README.md LICENSE models/ services/ ui/ assets/
```

### 3. Copy spec file

```bash
cp comic-strip-browser.spec ~/rpmbuild/SPECS/
```

### 4. Build the RPM

```bash
cd ~/rpmbuild/SPECS
rpmbuild -ba comic-strip-browser.spec
```

### 5. Find your RPMs

Binary RPM:
```
~/rpmbuild/RPMS/x86_64/comic-strip-browser-1.1.0-1.fc*.x86_64.rpm
```

Source RPM:
```
~/rpmbuild/SRPMS/comic-strip-browser-1.1.0-1.fc*.src.rpm
```

## Installing the RPM

### Using dnf (Fedora):
```bash
sudo dnf install ~/rpmbuild/RPMS/x86_64/comic-strip-browser-*.rpm
```

### Using rpm directly:
```bash
sudo rpm -ivh ~/rpmbuild/RPMS/x86_64/comic-strip-browser-*.rpm
```

## Uninstalling

```bash
sudo dnf remove comic-strip-browser
```

or

```bash
sudo rpm -e comic-strip-browser
```

## Spec File Details

The `comic-strip-browser.spec` file defines:

- **Package metadata**: Name, version, summary, license
- **Dependencies**: Python 3, PyQt6, requests, beautifulsoup4
- **Build process**: Uses PyInstaller to create standalone binary
- **Installation**: Installs binary, desktop file, icon, and documentation
- **Files**: Lists all files included in the package

## Troubleshooting

### Missing dependencies during build

If you get errors about missing Python modules:
```bash
pip3 install --user -r requirements.txt
```

### Permission errors

Make sure you have write permissions to `~/rpmbuild`:
```bash
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
chmod -R u+w ~/rpmbuild
```

### PyInstaller issues

If PyInstaller fails to build:
```bash
pip3 install --user --upgrade pyinstaller
```

## Distribution

The built RPM can be distributed and installed on:
- Fedora (all versions)
- RHEL 8+
- CentOS Stream 8+
- Rocky Linux 8+
- AlmaLinux 8+

Users will need to have the runtime dependencies installed (Python 3, PyQt6, etc.).
