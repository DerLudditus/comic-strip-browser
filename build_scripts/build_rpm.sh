#!/bin/bash
# Build script for creating RPM package for Comic Strip Browser

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Comic Strip Browser - RPM Build Script${NC}"
echo "========================================"

# Get version from version.py
VERSION=$(python3 -c "import sys; sys.path.insert(0, '.'); from version import __version__; print(__version__)")
echo -e "${YELLOW}Building version: ${VERSION}${NC}"

# Set up RPM build environment
RPMBUILD_DIR="${HOME}/rpmbuild"
echo "Setting up RPM build environment at ${RPMBUILD_DIR}"

# Create RPM build directory structure
mkdir -p "${RPMBUILD_DIR}"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
TARBALL_NAME="comic-strip-browser-${VERSION}.tar.gz"
echo "Creating source tarball: ${TARBALL_NAME}"

# Create temporary directory for tarball contents
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/comic-strip-browser-${VERSION}"
mkdir -p "${PACKAGE_DIR}"

# Copy project files to temporary directory
echo "Copying project files..."
cp -r \
    main.py \
    version.py \
    requirements.txt \
    comic_browser.spec \
    README.md \
    LICENSE \
    models/ \
    services/ \
    ui/ \
    assets/ \
    "${PACKAGE_DIR}/"

# Create tarball
cd "${TEMP_DIR}"
tar czf "${TARBALL_NAME}" "comic-strip-browser-${VERSION}"
mv "${TARBALL_NAME}" "${RPMBUILD_DIR}/SOURCES/"
cd - > /dev/null

# Clean up temporary directory
rm -rf "${TEMP_DIR}"

# Copy spec file to SPECS directory
echo "Copying spec file..."
cp comic-strip-browser.spec "${RPMBUILD_DIR}/SPECS/"

# Build the RPM
echo -e "${YELLOW}Building RPM package...${NC}"
cd "${RPMBUILD_DIR}/SPECS"
rpmbuild -ba comic-strip-browser.spec

# Check if build was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}RPM build completed successfully!${NC}"
    echo ""
    echo "RPM packages created:"
    echo "  Binary RPM: ${RPMBUILD_DIR}/RPMS/x86_64/comic-strip-browser-${VERSION}-1.*.x86_64.rpm"
    echo "  Source RPM: ${RPMBUILD_DIR}/SRPMS/comic-strip-browser-${VERSION}-1.*.src.rpm"
    echo ""
    
    # Copy RPMs to releases directory
    RELEASES_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")/releases"
    mkdir -p "${RELEASES_DIR}"
    
    echo "Copying RPMs to releases directory..."
    cp "${RPMBUILD_DIR}/RPMS/x86_64/comic-strip-browser-${VERSION}"-*.x86_64.rpm "${RELEASES_DIR}/"
    cp "${RPMBUILD_DIR}/SRPMS/comic-strip-browser-${VERSION}"-*.src.rpm "${RELEASES_DIR}/"
    
    echo -e "${GREEN}RPMs copied to: ${RELEASES_DIR}${NC}"
else
    echo -e "${RED}RPM build failed!${NC}"
    exit 1
fi
