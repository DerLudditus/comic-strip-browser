Name:           comic-strip-browser
Version:        1.1.3
Release:        1.fc42
Summary:        A standalone comic strip browser for 20 titles from GoComics.com

License:        MIT
URL:            https://github.com/DerLudditus/comic-strip-browser
Source0:        %{name}-%{version}.tar.gz
Packager:       Homo Ludditus <ludditus@etik.com>

BuildArch:      x86_64
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  python3-setuptools
BuildRequires:  python3-virtualenv
BuildRequires:       python3
#BuildRequires:       python3-pyqt6
#BuildRequires:       python3-requests
#BuildRequires:       python3-beautifulsoup4

%description
A standalone PyQt6 application for browsing a selection of comic strips from
GoComics.com. Features include calendar navigation, caching, and support for
15 popular comic strips including Calvin and Hobbes, Peanuts, Garfield, and more.

%global debug_package %{nil}

%prep
%autosetup

%build
# Build the binary using PyInstaller
python3 -m venv build_venv
source build_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pyinstaller comic_browser.spec
deactivate

%install
# Install the binary
install -D -m 0755 dist/comic-strip-browser %{buildroot}%{_bindir}/comic-strip-browser

# Install desktop file
install -D -m 0644 assets/comic-strip-browser.desktop %{buildroot}%{_datadir}/applications/comic-strip-browser.desktop

# Install icon
install -D -m 0644 assets/comic-strip-browser.png %{buildroot}%{_datadir}/pixmaps/comic-strip-browser.png

%files
%license LICENSE
%doc README.md
%{_bindir}/comic-strip-browser
%{_datadir}/applications/comic-strip-browser.desktop
%{_datadir}/pixmaps/comic-strip-browser.png

%changelog
* Fri Nov 14 2025 Homo Ludditus <ludditus@etik.com> - 1.1.3-1
- Removed Wizard of Id Classics because GoComics stopped publishing it on Oct. 31 (it was a reprint, anyway)
- Number of strip titles: 20

* Fri Nov 14 2025 Homo Ludditus <ludditus@etik.com> - 1.1.2-1
- Added 6 more comic strip titles, to a total of 21

* Tue Oct 21 2025 Homo Ludditus <ludditus@etik.com> - 1.1.1-1
- Updated the start dates of each comic regarding their presence on GoComics
- Added "First" and "Random" buttons for navigation
- Added smart Next/Previous navigation that skips gaps
- Added global keyboard shortcuts (Left/Right arrows: Previous/Next, Home/End: First/Today)
- Fixed image format detection (now detects PNG/GIF correctly, so cached files have the correct extension)
- Improved performance
- Fixed the status bar
- Removed the logging
- Various UI improvements and bug fixes
- Race conditions could still made the app "forget" the currently selected comic title on occasions

* Fri Jul 25 2025 Homo Ludditus <ludditus@etik.com> - 1.0.4-1
- Added the 15th comic strip title
- Initial RPM release
