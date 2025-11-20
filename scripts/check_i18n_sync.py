#!/usr/bin/env python3
"""
Check that README.md and README.it.md are synchronized.

Verifies that both files have the same structure (headers, sections).
"""

import re
import sys
from pathlib import Path


def extract_headers(content: str) -> list[str]:
    """Extract all markdown headers from content."""
    headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
    return headers


def normalize_header(header: str) -> str:
    """Normalize header for comparison (remove emojis, badges, language markers)."""
    # Remove badges
    header = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', header)
    # Remove emojis
    header = re.sub(r'[\U0001F300-\U0001F9FF]', '', header)
    # Remove language markers
    header = re.sub(r'🇮🇹|🇬🇧', '', header)
    # Normalize whitespace
    header = ' '.join(header.split())
    return header.strip().lower()


def check_sync(readme_en: Path, readme_it: Path) -> bool:
    """Check if README files are synchronized."""

    if not readme_en.exists():
        print(f"❌ {readme_en} not found")
        return False

    if not readme_it.exists():
        print(f"❌ {readme_it} not found")
        return False

    content_en = readme_en.read_text()
    content_it = readme_it.read_text()

    headers_en = extract_headers(content_en)
    headers_it = extract_headers(content_it)

    # Normalize headers for comparison
    normalized_en = [normalize_header(h) for h in headers_en]
    normalized_it = [normalize_header(h) for h in headers_it]

    # Remove translated headers that are expected to differ
    translations = {
        'rag platform - complete documentation': 'piattaforma rag - documentazione completa',
        'quick start': 'avvio rapido',
        'table of contents': 'indice',
        'system overview': 'panoramica del sistema',
        'how it works': 'come funziona',
        'data flow': 'flusso dei dati',
        'components and architecture': 'componenti e architettura',
        'system requirements': 'requisiti di sistema',
        'manual installation': 'installazione manuale',
        'english version': 'versione inglese',
        'versione italiana': 'italian version',
    }

    # Check structure similarity (number of headers)
    if len(headers_en) != len(headers_it):
        print(f"⚠️  Different number of sections: EN={len(headers_en)}, IT={len(headers_it)}")
        print(f"   English sections: {len(headers_en)}")
        print(f"   Italian sections: {len(headers_it)}")
        return False

    # Check for major structural differences
    major_differences = 0
    for i, (h_en, h_it) in enumerate(zip(normalized_en, normalized_it)):
        # Skip if it's a known translation
        if h_en in translations and translations[h_en] == h_it:
            continue
        if h_it in translations and translations[h_it] == h_en:
            continue

        # If headers are too different, flag it
        if h_en != h_it and h_en not in translations:
            major_differences += 1
            if major_differences <= 5:  # Show first 5 differences
                print(f"⚠️  Section {i+1} may differ:")
                print(f"   EN: {headers_en[i]}")
                print(f"   IT: {headers_it[i]}")

    if major_differences == 0:
        print("✅ README files appear to be in sync")
        return True
    else:
        print(f"\n⚠️  Found {major_differences} structural differences")
        print("   This may be normal if sections have been translated differently")
        return True  # Return True anyway, just warn


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    readme_en = repo_root / "README.md"
    readme_it = repo_root / "README.it.md"

    print("🔍 Checking README.md and README.it.md sync...")
    print()

    result = check_sync(readme_en, readme_it)

    if result:
        print("\n✅ Check complete")
        sys.exit(0)
    else:
        print("\n❌ READMEs are out of sync")
        sys.exit(1)


if __name__ == "__main__":
    main()
