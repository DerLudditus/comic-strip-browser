# GitHub Actions Build Automation

This project uses GitHub Actions to automatically build releases for Windows and Linux.

## Workflows

### 1. Test Build (`test-build.yml`)

Runs on every push to main/master/develop branches and on pull requests.

**What it does:**
- Tests Windows build using cx_Freeze
- Tests Linux build using PyInstaller
- Verifies executables are created successfully
- Does NOT create releases

**Trigger:** Automatic on push/PR

### 2. Build Releases (`build-releases.yml`)

Creates release builds for distribution.

**What it does:**
- Builds Windows executable (cx_Freeze) → ZIP archive
- Builds Linux binary (PyInstaller) → included in DEB/RPM
- Builds DEB package for Debian/Ubuntu
- Builds RPM package for Fedora/RHEL
- Creates GitHub Release with all artifacts (only on tags)

**Triggers:**
- Automatic when you push a version tag (e.g., `v1.1.0`)
- Manual via GitHub Actions UI

## How to Create a Release

### Method 1: Push a Tag (Recommended)

```bash
# Update version in version.py first
git add version.py
git commit -m "Bump version to 1.1.0"
git push

# Create and push tag
git tag v1.1.0
git push origin v1.1.0
```

This will:
1. Trigger the build workflow
2. Build all packages (Windows ZIP, DEB, RPM)
3. Create a GitHub Release
4. Upload all artifacts to the release

### Method 2: Manual Trigger

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select "Build Releases" workflow
4. Click "Run workflow" button
5. Select branch and click "Run workflow"

This builds the packages but does NOT create a release (only tags do that).

## Artifacts

After a successful build, you'll get:

### Windows
- `ComicStripBrowser-1.1.0-Windows.zip` - Portable Windows application
  - Extract and run `ComicStripBrowser.exe`
  - Includes all dependencies

### Linux
- `comic-strip-browser_1.1.0-1_amd64.deb` - Debian/Ubuntu package
  - Install: `sudo apt install ./comic-strip-browser_*.deb`
  
- `comic-strip-browser-1.1.0-1.fc42.x86_64.rpm` - Fedora/RHEL package
  - Install: `sudo dnf install comic-strip-browser-*.rpm`

## Viewing Build Results

### For Test Builds
1. Go to "Actions" tab
2. Click on the latest workflow run
3. Check if all jobs passed (green checkmarks)

### For Release Builds
1. Go to "Actions" tab to see build progress
2. Once complete, go to "Releases" tab
3. Download artifacts from the release page

## Troubleshooting

### Build fails on Windows

Check the workflow logs:
1. Go to Actions → Failed workflow
2. Click on "build-windows" job
3. Expand failed step to see error

Common issues:
- Missing dependencies → Check `requirements.txt`
- cx_Freeze errors → Check `setup_cxfreeze.py`

### Build fails on Linux

Check the workflow logs for:
- PyInstaller errors → Check `comic_browser.spec`
- Missing system packages → Update workflow to install them

### Release not created

Releases are only created when you push a tag starting with `v`:
```bash
git tag v1.1.0
git push origin v1.1.0
```

### Artifacts not uploaded

Check that:
- Build completed successfully
- Artifact paths in workflow match actual output locations
- You have proper GitHub permissions

## Local Testing

Before pushing, test builds locally:

**Windows:**
```cmd
build_scripts\build_windows_cxfreeze.bat
```

**Linux:**
```bash
./build_scripts/build_linux.sh
python build_scripts/create_deb.py
./build_scripts/build_rpm.sh
```

## Customization

### Change Python version

Edit both workflow files:
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'  # Change this
```

### Add more platforms

Add new jobs to `build-releases.yml`:
```yaml
build-macos:
  runs-on: macos-latest
  steps:
    # ... build steps
```

### Change artifact names

Edit the version output and file naming in the workflows.

## GitHub Secrets

No secrets are required for basic builds. The workflow uses:
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Costs

GitHub Actions is free for public repositories with generous limits:
- 2,000 minutes/month for private repos
- Unlimited for public repos

Each build takes approximately:
- Windows: 5-10 minutes
- Linux: 3-5 minutes
- Total: ~15 minutes per release
