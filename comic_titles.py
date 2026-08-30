#!/usr/bin/env python3
"""
comic_titles.py - Generates COMIC_TITLES.md from models/data_models.py.

This standalone utility parses COMIC_DEFINITIONS from models.data_models and
generates a markdown document (COMIC_TITLES.md) containing:
1. The exact formatted numbered list for copying into README.md.
2. A detailed reference table with metadata, authors, earliest dates, and sources.
3. Summary statistics (total titles, provider breakdown).

Usage:
    python comic_titles.py
"""

import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from models.data_models import COMIC_DEFINITIONS
except ImportError as e:
    print(f"Error importing COMIC_DEFINITIONS: {e}", file=sys.stderr)
    sys.exit(1)


def get_provider_name(comic_def) -> str:
    """Determine the provider label for a comic definition."""
    if " | " in comic_def.display_name:
        return comic_def.display_name.split(" | ", 1)[1].strip()
    if getattr(comic_def, 'is_custom', False):
        domain = urlparse(comic_def.base_url).netloc.replace("www.", "")
        return domain or "Custom"
    elif "comicskingdom.com" in comic_def.base_url.lower():
        return "CK"
    elif "gocomics.com" in comic_def.base_url.lower():
        return "GoComics"
    else:
        domain = urlparse(comic_def.base_url).netloc.replace("www.", "")
        return domain or "Other"


def format_readme_entry(index: int, comic_def) -> str:
    """Format a comic entry matching the exact style in README.md."""
    display_name = comic_def.display_name
    if " | " in display_name:
        clean_name, at_part = display_name.split(" | ", 1)
        return f"{index}. **{clean_name}** | {at_part}"
    else:
        provider = get_provider_name(comic_def)
        return f"{index}. **{display_name}** | {provider}"


from collections import Counter


def generate_markdown(output_file: Path) -> None:
    """Generate the COMIC_TITLES.md file."""
    total_comics = len(COMIC_DEFINITIONS)
    
    # Calculate title frequency and statistics
    clean_titles = [c.display_name.split(" | ")[0].strip() for c in COMIC_DEFINITIONS]
    title_counts = Counter(clean_titles)
    unique_titles_count = len(title_counts)
    multi_site_count = sum(1 for count in title_counts.values() if count > 1)

    gocomics_count = sum(1 for c in COMIC_DEFINITIONS if get_provider_name(c).lower() == "gocomics")
    ck_count = sum(1 for c in COMIC_DEFINITIONS if get_provider_name(c).lower() == "ck")
    custom_count = total_comics - gocomics_count - ck_count
    
    lines = []
    lines.append("# Supported Comic Strips Reference")
    lines.append("")
    lines.append("---")
    lines.append("")    
    lines.append(f"> Auto-generated from `models/data_models.py` by `comic_titles.py` on {datetime.now().strftime('%Y-%m-%d')}.")
    lines.append(f"> **Total Titles:** {total_comics} | **Unique Titles:** {unique_titles_count} | **Multi-Site Titles:** {multi_site_count} | **GoComics:** {gocomics_count} | **Comics Kingdom:** {ck_count} | **Other/Custom:** {custom_count}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 1. List of comics")
    lines.append("")
    for i, comic_def in enumerate(COMIC_DEFINITIONS, 1):
        lines.append(format_readme_entry(i, comic_def))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 2. Detailed list of comics")
    lines.append("")
    lines.append("| # | Title | Slug (`name`) | Source | Author | Earliest&nbsp;Date |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for i, comic_def in enumerate(COMIC_DEFINITIONS, 1):
        provider = get_provider_name(comic_def)
        earliest = comic_def.earliest_date.strftime("%Y-%m-%d") if comic_def.earliest_date else "N/A"
        clean_author = comic_def.author.replace("|", "/")
        clean_title = comic_def.display_name.split(" | ")[0] if " | " in comic_def.display_name else comic_def.display_name
        clean_title = clean_title.replace("|", "/")
        lines.append(f"| {i} | **{clean_title}** | `{comic_def.name}` | {provider} | {clean_author} | {earliest} |")
    
    lines.append("")
    
    content = "\n".join(lines) + "\n"
    output_file.write_text(content, encoding="utf-8")
    print(f"[OK] Generated {output_file.name} successfully ({total_comics} titles).")


def main():
    output_path = PROJECT_ROOT / "COMIC_TITLES.md"
    generate_markdown(output_path)


if __name__ == "__main__":
    main()
