# Comic Strip Browser — Architecture & Design Guide

This document is the single architectural reference for the Comic Strip Browser application. It describes all core subsystems, data structures, calendar availability engines, scraping pipelines, image scaling mathematics, caching lifecycles, and UI controllers.

---

## 1. System Architecture Overview

The application is structured as a **Layered Model-View-Controller (MVC) / Service-Oriented Architecture** built with **PyQt6**:

```text
+-------------------------------------------------------------------------+
|                                UI LAYER                                 |
|  MainWindow  |  ComicViewer  |  CalendarWidget  |  ComicSelector        |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                            CONTROLLER LAYER                             |
|                             ComicController                             |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                        SERVICE ORCHESTRATION LAYER                      |
|                                ComicService                             |
+-------------------------------------------------------------------------+
       |                  |                 |                  |
       v                  v                 v                  v
+--------------+  +---------------+  +--------------+  +------------------+
| CacheManager |  |  WebScraper   |  | ConfigManager|  |   DateManager    |
|  (Disk LRU)  |  | (GoComics/CK/ |  | (Start Dates |  | (Earliest Date   |
|              |  |    Custom)    |  |  & Settings) |  |    Discovery)    |
+--------------+  +---------------+  +--------------+  +------------------+
       |                  |
       +--------+---------+
                |
                v
+-------------------------------------------------------------------------+
|                               DATA MODELS                               |
|              ComicDefinition  |  ComicData  |  CacheEntry               |
+-------------------------------------------------------------------------+
```

---

## 2. Directory Structure & File Map

| File Path | Responsibility & Key Exports |
| :--- | :--- |
| **`main.py`** | Application entry point, CLI argument parsing (`--debug`, `--future`), service dependency injection, global exception handlers, Qt event loop execution. |
| **`version.py`** | Single source of truth for version number (`__version__`), release metadata, and Debian package changelog. |
| **`models/data_models.py`** | Dataclasses for comic definitions (`ComicDefinition`), fetched comics (`ComicData`), disk cache records (`CacheEntry`), and the registry array `COMIC_DEFINITIONS`. |
| **`services/comic_service.py`** | Central service orchestrating cache lookup, web scraping, and recursive 7-day date fallback with true-date binding. |
| **`services/web_scraper.py`** | HTTP requests engine, HTML parser for GoComics / Comics Kingdom `og:image` tags, security challenge detection, and direct custom URL generators. |
| **`services/cache_manager.py`** | Manages `cache/{comic_name}/` disk storage, LRU eviction (50 images per strip), image downloading, format sniffing, and `cache_index.json`. |
| **`services/date_manager.py`** | Probing engine that discovers the earliest available publication date for each strip via binary/step search. |
| **`services/config_manager.py`** | Reads/writes user configurations, window geometry, and cached earliest dates to JSON (`~/.comic_browser_config.json`). |
| **`services/error_handler.py`** | Exception taxonomy (`ComicUnavailableError`, `NetworkError`, `ParsingError`, `CacheError`), severity levels, and user-facing messages. |
| **`ui/main_window.py`** | 3-pane main window container, menu bar, status bar, action buttons (Open Cache, Delete Cache, About), and keyboard navigation handlers. |
| **`ui/comic_viewer.py`** | Main comic display canvas, navigation buttons, image scaling engine (`calculate_display_size`), DPR physical resampling, loading/error UI states. |
| **`ui/comic_controller.py`** | Qt Controller executing comic loading on background threads (`QThread`), updating progress bars, and emitting UI refresh signals. |
| **`ui/comic_selector.py`** | Left sidebar comic list with real-time text search filter, title badges, and comic selection signals. |
| **`ui/calendar_widget.py`** | Custom grid calendar for date selection with dynamic availability coloring, quick year/month selectors, and gap detection. |
| **`ui/about_dialog.py`** | Modal dialog presenting app details, system information, licensing, and full release changelog. |

---

## 3. Data Models & Availability Engine (`models/data_models.py`)

### 3.1 `ComicDefinition`
`ComicDefinition` holds all static metadata, publishing schedules, syndication transition rules, and custom source definitions.

#### Metadata Fields
* `name` *(str)*: Unique lowercase identifier slug (e.g. `"calvinandhobbes"`, `"mother-goose-and-grimm"`, `"shoe3"`).
* `display_name` *(str)*: User-facing name (e.g. `"Calvin and Hobbes"`, `"Shoe @ ShoeComics"`).
* `base_url` *(str)*: Syndication root URL or custom provider base URL.
* `author` *(str)*: Creator / syndicate author attribution.
* `earliest_date` *(Optional[date])*: The hard lower bound for calendar navigation.
* `info` *(str)*: Explanatory text shown in the About/Info panels.
* `never_scale_up` *(bool)*: If True, prevents upscaling small images to 900px width.

#### Complex Availability & Calendar Rule Properties
Comic publishing schedules are historically complex. `ComicDefinition` models these schedules via specific rule fields:

| Field | Type | Description & Example |
| :--- | :--- | :--- |
| `skip_ranges` | `List[Tuple[str, str]]` | Date intervals `(start_iso, end_iso)` where the comic was on sabbatical or unavailable.<br>*Example:* Calvin and Hobbes sabbaticals `[("1991-05-05", "1992-02-01"), ("1994-04-03", "1994-12-31")]`. |
| `skip_days` | `Tuple[str, ...]` or `str` | Specific one-off missing dates.<br>*Example:* `("1998-01-18",)` for *The Fusco Brothers*. |
| `dates_one_off` | `Tuple[str, ...]` or `str` | Discontinuous launch teaser dates before regular syndication began.<br>*Example:* `("2001-11-03", "2002-01-01", "2002-01-02")` for *Flo and Friends*. |
| `weekly_between` | `Tuple[str, str]` | Date range where strip ran **Sundays only**.<br>*Example:* `("1996-01-07", "1998-10-04")` for *The Family Circus*. |
| `daily_between` | `Tuple[str, str]` | Date range where strip ran daily.<br>*Example:* `("1988-04-11", "2006-12-31")` for *Foxtrot*. |
| `daily_since` | `date` | Date from which the comic transitioned to daily publication. |
| `daily_since_no_sundays` | `date` | Daily publication excluding Sundays prior to syndication launch. |
| `weekly_since` | `date` | Date from which the comic became Sunday-only.<br>*Example:* `date(2007, 1, 7)` for *Foxtrot*. |
| `normal_is_sundays` | `str` (`"true"`/`""`) | Strip is published exclusively on Sundays (*Prince Valiant*). |
| `never_on_sundays` | `str` (`"true"`/`""`) | Strip is published Monday–Saturday only (*Foxtrot Classics*). |
| `never_on_saturdays` | `str` (`"true"`/`""`) | Strip is published Monday–Friday only (*Savage Chickens*). |

#### Availability Evaluation Engine (`is_available`)
`ComicDefinition.is_available(check_date: date) -> bool` evaluates dates through a strict **Precedence Hierarchy**:

1. **Bounds Check:** If `check_date < earliest_date` or `check_date > today` (or `today + 1` if `COMIC_BROWSER_ALLOW_FUTURE` is set) $\to$ **False**.
2. **Explicit Skip Ranges (Highest Priority):** If `check_date` falls inside any `skip_ranges` $\to$ **False**.
3. **Explicit Skip Days:** If `check_date` matches `skip_days` $\to$ **False**.
4. **One-Off Dates:** If `check_date` matches `dates_one_off` $\to$ **True**.
5. **Interval Matching:**
   * `weekly_between`: True only if `check_date.weekday() == 6` (Sunday).
   * `daily_between`: True on all days (or False on Sundays if `never_on_sundays="true"`).
   * `daily_since`: True on all days (or False on Sundays if `never_on_sundays="true"`).
   * `daily_since_no_sundays`: True, but skips Sundays if before `daily_since`.
   * `weekly_since`: True only if `check_date.weekday() == 6`.
6. **Default Fallback:**
   * If intervals are defined but none matched $\to$ **False** (it's a gap).
   * If no intervals are defined $\to$ evaluate `normal_is_sundays` and `never_on_sundays`.

---

### 3.2 Custom Provider Subsystem (`is_custom` & `custom_url_pattern`)

For comics hosted on dedicated author servers rather than GoComics or Comics Kingdom:
* `is_custom = True`: Directs the scraper to bypass HTML web page fetching and BeautifulSoup parsing.
* `custom_url_pattern`: Template string with macro tokens:
  * `%YYYY%` $\to$ 4-digit year (e.g. `2009`)
  * `%YY%` $\to$ 2-digit year (e.g. `09` or `26`)
  * `%MM%` $\to$ 2-digit month (e.g. `01`)
  * `%DD%` $\to$ 2-digit day (e.g. `02`)

#### Custom Provider Configurations
1. **Mother Goose and Grimm (`grimmy.com`):**
   * `base_url`: `"https://www.grimmy.com"`
   * `custom_url_pattern`: `"/images/MGG_Archive/MGG_%YYYY%/MGG-%YYYY%-%MM%-%DD%.gif"`
   * *Target URL:* `https://www.grimmy.com/images/MGG_Archive/MGG_2009/MGG-2009-01-02.gif`
2. **Shoe @ ShoeComics (`shoecomics.com`):**
   * `base_url`: `"https://www.shoecomics.com"`
   * `custom_url_pattern`: `"/archives/shoe_daily/shoe_daily%MM%%DD%%YY%.jpg"`
   * *Target URL:* `https://www.shoecomics.com/archives/shoe_daily/shoe_daily082426.jpg`

---

## 4. Service Layer Subsystems

### 4.1 Comic Retrieval & 7-Day Fallback Pipeline (`services/comic_service.py`)

`ComicService.get_comic(comic_name, comic_date, _depth=0)` coordinates fetching, disk caching, and gap recovery.

#### Step-by-Step Retrieval Lifecycle:
```text
UI (Viewer)        ComicController      ComicService         CacheManager         WebScraper
    |                     |                  |                    |                   |
    |--- load_comic ----->|                  |                    |                   |
    |                     |--- get_comic --->|                    |                   |
    |                     |                  |-- get_cached_comic>|                   |
    |                     |                  |<-- Cache Hit ------|                   |
    |                     |                  |    (Return cached) |                   |
    |                     |                  |                    |                   |
    |                     |                  |-- Cache Miss ------------------------->|
    |                     |                  |<-- ComicData (HTTP 200 OK) ------------|
    |                     |                  |-- cache_comic ---->|                   |
    |                     |                  |                    |                   |
    |                     |                  |-- (If 404/Gap) ----------------------->|
    |                     |                  |<-- WebScrapingError -------------------|
    |                     |                  |                                        |
    |                     |                  |-- Fallback: Recurse for yesterday ---->|
    |                     |                  |   (Repeats up to 7 days depth)         |
    |                     |                  |                                        |
    |                     |<-- ComicData ----|                                        |
    |<-- display_comic ---|                  |                                        |
```

1. **Cache Inspection:** Checks `cache_manager.get_cached_comic()`. On hit, returns `ComicData` instantly.
2. **Web Request:** Calls `web_scraper.get_comic_data()`.
3. **Recursive 7-Day Backward Fallback:**
   * If fetching fails (HTTP 404, date mismatch redirect, or `ComicUnavailableError`):
   * If `_depth < 7`, calculates `yesterday = comic_date - 1 day` and calls `get_comic(comic_name, yesterday, _depth + 1)`.
   * **Date-Binding Rule:** Because `get_comic` recurses with the earlier date, the returned `ComicData.date` reflects the **actual publication date found**. The image is cached under this actual date, and the calendar highlights the true date.
4. **Cache Write:** The retrieved image is saved to disk and indexed in `cache_index.json`.

---

### 4.2 Web Scraping Engine (`services/web_scraper.py`)

Handles network communication across different provider protocols:

1. **Custom Providers (`is_custom=True`):**
   * Assembles the image URL by replacing `%YYYY%`, `%YY%`, `%MM%`, `%DD%`.
   * Sends an HTTP `HEAD` request (falling back to a streamed `GET` on `405 Method Not Allowed`) to confirm HTTP 200 OK without downloading the full image into RAM.
   * On HTTP 404, raises `WebScrapingError("Comic not available for this date")` to trigger the fallback engine.
2. **GoComics (`gocomics.com`):**
   * URL format: `{base_url}/{YYYY}/{MM}/{DD}`.
   * Disables HTTP redirects for past dates to catch missing-strip redirects.
   * Parses HTML with BeautifulSoup to find `<meta property="og:image" content="...">`.
   * Detects Bunny.net / Cloudflare IP security challenges:
     `"security service" in page_text and ("secure connection" in page_text or "Please enable JavaScript" in page_text)`.
3. **Comics Kingdom (`comicskingdom.com`):**
   * URL format: `{base_url}/{YYYY}-{MM}-{DD}`.
   * Checks `og:url`, canonical `<link>`, and `<meta id="__next-page-redirect">` against the requested date to prevent displaying cached/redirected content from wrong dates.

---

### 4.3 Caching Subsystem (`services/cache_manager.py`)

* **Storage Path:** Relative directory `cache/{comic_name}/`.
* **Metadata Index:** `cache/{comic_name}/cache_index.json` maps dates (`"YYYY-MM-DD"`) to `CacheEntry` objects containing `last_accessed` timestamps, image path, dimensions, and author.
* **LRU Eviction Policy:**
  * Limits cache storage to **50 items per comic strip**.
  * When entry count $> 50$, sorts entries by `last_accessed` ascending, deletes the oldest physical image files from disk, and updates `cache_index.json`.
* **Format Sniffing:** Automatically detects and normalizes JPEG/PNG/GIF/WebP formats during download.

---

## 5. UI Architecture & Image Scaling

### 5.1 Image Scaling & Display Pipeline (`ui/comic_viewer.py`)

The scaling engine in `calculate_display_size()` and `display_image()` handles diverse strip shapes (single-panel square, 3-panel strip, tall portrait) and fractional HiDPI desktop displays:

```text
  [ Original QPixmap (w, h) ]
               |
               v
  +--------------------------+          YES
  | Is Aspect Diff <= 16% ?  | ------------------------+
  | (Single-Panel / Square)  |                         |
  +--------------------------+                         v
               | NO                         +----------------------+
               v                            | Single-Panel Rule:   |
  +--------------------------+              | Cap width to max 600 |
  | Huge Image (w > 1535px)? |              +----------------------+
  +--------------------------+                         |
      | Landscape      | Portrait                      |
      v                v                               |
+---------------+ +-------------------------+          |
| Width = 1200  | | Factor 0.35x/0.45x/0.50x|          |
| Height scaled | | Floor width at min 600px|          |
+---------------+ +-------------------------+          |
      |                        |                       |
      +------------+-----------+                       |
                   |                                   |
                   | NO (w <= 1535px)                  |
                   v                                   |
  +--------------------------------+                   |
  | Target Width Rules:            |                   |
  | - Portrait: min 450px          |                   |
  | - Landscape: min 900px         |                   |
  | - 450px <= w <= 600px: no scale|                   |
  +--------------------------------+                   |
                   |                                   |
                   +-----------------+-----------------+
                                     |
                                     v
                 +----------------------------------------+
                 | Window Constraint:                     |
                 | If w > max_w: scale down to fit window |
                 +----------------------------------------+
                                     |
                                     v
                 +----------------------------------------+
                 | Logical Display Size (w, h)            |
                 +----------------------------------------+
                                     |
                                     v
                 +----------------------------------------+
                 | HiDPI / DPR Transformation:            |
                 | physical_size = logical_size * DPR     |
                 | setDevicePixelRatio(DPR)               |
                 +----------------------------------------+
                                     |
                                     v
                 +----------------------------------------+
                 | Render Crisp QPixmap in QLabel         |
                 +----------------------------------------+
```

#### Detailed Sizing Rules:
1. **Single-Panel / Square Heuristic:**
   * Condition: `abs(w - h) / max(w, h) <= 0.16`.
   * Scales down large images ($w > 600\text{px}$) to `600px` width. Prevents square strips (*The Family Circus*, *Dennis The Menace*, *Ziggy*) from overflowing vertically.
2. **Huge Portraits ($w > 1535\text{px}$ and $w < h$):**
   * Scales by $0.35\times, 0.45\times, 0.50\times$, with a strict floor enforcing `w >= 600px`.
3. **Narrow Vertical Strips ($450 \le w \le 600\text{px}$):**
   * Preserves natural width (e.g. $512 \times 2048$) to prevent height explosion.
4. **Standard Horizontal Strips ($w \ge h$):**
   * Target minimum width is `900px` (unless `never_scale_up=True`).
5. **Window Constraint (`max_w = viewport.width() - 40`):**
   * Downscales proportionally if wider than window; never upscales to fill window.
6. **Centering & Layout Alignment:**
   * `QScrollArea` uses `setWidgetResizable(False)` with `AlignHCenter | AlignTop`.
   * `_resize_content_widget()` manually resizes the content container to its layout `totalSizeHint()`, enabling horizontal centering.
7. **HiDPI / Fractional Scaling:**
   * Multiplies logical size by `dpr = window().devicePixelRatioF()`.
   * Resamples image to physical resolution via `Qt.TransformationMode.SmoothTransformation`.
   * Tags the `QPixmap` with `setDevicePixelRatio(dpr)` so Qt maps physical pixels 1:1 without compositor blur.

---

### 5.2 Calendar Widget (`ui/calendar_widget.py`)

* **Day Cell States & Color Coding:**
  * **Selected Day:** Solid Blue (`#2196f3`) with white text.
  * **Unavailable Day:** Solid Gray (`#f0f0f0`) with gray text (`#c0c0c0`), disabled/unclickable.
  * **Today:** White background with Orange outline (`#ff9800`).
  * **Normal Available Day:** White background with gray border (`#e0e0e0`).
* **Evaluation:** On month change, evaluates `comic_def.is_available(date)` for every day cell.

---

### 5.3 Navigation & Gap-Jumping Algorithms (`ui/main_window.py`)

#### Sequential Navigation (Next / Previous / Arrow Keys)
* Iterates day-by-day in direction of travel.
* **Skip Range Jumping:** If candidate date hits `skip_ranges`, jumps immediately to the day after the gap (`range_end + 1 day`), avoiding hundreds of individual failed HTTP checks.
* Bounds travel to `earliest_date` and `today` (or `tomorrow` with `--future`).

#### The Random Navigation Algorithm (`go_to_random`)
1. Calculates available span: `days_available = (today - earliest_date).days`.
2. **Phase 1 (Availability Probing):** Attempts up to 100 random date selections checked against `comic_def.is_available(candidate_date)`.
3. **Phase 2 (Forward Gap Resolution):** If selected date hits an uncataloged syndicate gap, traverses forward up to 7 days until an image successfully loads.

---

## 6. Keyboard Shortcuts & CLI Interface

### 6.1 Keyboard Navigation Shortcuts

| Shortcut | Function |
| :--- | :--- |
| **Left Arrow** | Navigate to Previous comic date |
| **Right Arrow** | Navigate to Next comic date |
| **Home** | Jump to Earliest available date for the selected comic |
| **End** | Jump to Today's date |
| **Page Up** | Select Previous comic title in list (cycles at top) |
| **Page Down** | Select Next comic title in list (cycles at bottom) |
| **F1** | Open About dialog and release changelog |

---

### 6.2 Command-Line Interface (CLI) & Headless Batch Operations

The application supports a powerful **headless CLI mode** (`main.py` / binary) for listing comic metadata and batch downloading/caching comic strips without launching the Qt GUI:

#### Information & Listing Commands
* **`--names`**: Prints all 96 internal comic identifier slugs (one per line). Useful for scripting and automation.
* **`--info`**: Prints all 96 comics formatted with their 1-based GUI index, internal name slug, and display title:
  `number=X | name=Y | display_name=Z`
* **`-h` / `--help`**: Displays command-line argument help.

#### Headless Batch & Single Comic Downloading
When downloading in CLI mode, if the target date is not a publication day, the downloader automatically probes backwards up to 31 days (`_find_latest_available_date`) to fetch the latest published strip.
* **`--all`**: Downloads and caches all 96 comics in headless mode.
* **`--name=*name*`**: Downloads and caches a single comic by its internal name slug (e.g. `--name=baldo` or `--name=calvinandhobbes`).
* **`--number=*id*`**: Downloads and caches a single comic by its 1-based GUI index (1–96, e.g. `--number=8`).

#### Date Selectors (Mutually Exclusive)
* **`--today`** *(default)*: Targets today's comic publication.
* **`--yesterday`**: Targets yesterday's comic publication.

#### Debugging & Environment Flags
* **`--debug`**: Enables verbose debug logging to console and `comic_browser.log`.
* **`--future`**: Sets `COMIC_BROWSER_ALLOW_FUTURE=1`, enabling navigation to tomorrow's date for time-zone gap testing.

#### Example CLI Invocations
```bash
# Print list of all comic names
python3 main.py --names

# Print numbered info list (1-96)
python3 main.py --info

# Download and cache all 96 comics for today
python3 main.py --all --today

# Download yesterday's Garfield strip by slug
python3 main.py --name=garfield --yesterday

# Download comic #20 (Calvin and Hobbes) for today
python3 main.py --number=20 --today

# Run GUI with verbose debug logging enabled
python3 main.py --debug
```

---

## 7. Packaging & Distribution

The application is built and packaged across multiple targets using PyInstaller and GitHub Actions CI:

* **Linux Binaries & Packages:** Single-file binary, `.deb` (Debian/Ubuntu), `.rpm` (Fedora/RHEL), and standalone `.AppImage`.
* **Linux AppImage Support:** `_open_cache_folder()` cleans `LD_LIBRARY_PATH`, `PYTHONPATH`, and `PYTHONHOME` before calling `xdg-open` to prevent library clashes with host system file managers.
* **Windows:** Standalone single-file executable `ComicStripBrowser.exe` built via `build_scripts/build_windows.bat` and `comic_browser.spec`.

---

## 8. Python Dependencies & Execution Environment

To run the application directly from Python source code (`python3 main.py`), the following libraries are required:

### Linux (Debian / Ubuntu / Linux Mint)
Using system packages:
```bash
sudo apt install python3-pyqt6 python3-bs4 python3-pil python3-requests
```

### Windows
Using `pip`:
```bash
pip install PyQt6 bs4 requests pillow
```

### Standard `requirements.txt`
```text
PyQt6>=6.4.0
requests>=2.31.0
beautifulsoup4>=4.12.0
pillow>=10.0.0
pytest>=7.4.0
pyinstaller>=6.0.0
```
