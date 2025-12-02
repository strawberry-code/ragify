#!/usr/bin/env python3
"""
Tika availability checker and installer.
Verifies Java and Tika dependencies before processing.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def check_java_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if Java is installed and get version.

    Returns:
        Tuple of (is_installed, version_string)
    """
    try:
        result = subprocess.run(
            ['java', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Java prints version to stderr
        version_output = result.stderr or result.stdout

        if result.returncode == 0:
            # Extract version number
            version_line = version_output.split('\n')[0]
            return True, version_line
        else:
            return False, None

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def check_tika_jar_available() -> Tuple[bool, Optional[Path]]:
    """
    Check if Tika JAR is already downloaded.

    Returns:
        Tuple of (is_available, jar_path)
    """
    # Check environment variable first (for Docker containers)
    env_path = os.getenv('TIKA_JAR_PATH')
    if env_path:
        jar_path = Path(env_path)
        if jar_path.exists():
            logger.debug(f"Tika JAR found via TIKA_JAR_PATH: {jar_path}")
            return True, jar_path

    # Static paths to check
    static_paths = [
        Path('/tmp/tika-server.jar'),
        Path.home() / '.tika' / 'tika-server.jar',
    ]

    for path in static_paths:
        if path.exists():
            logger.debug(f"Tika JAR found at: {path}")
            return True, path

    # Glob patterns for versioned JARs (tika-server-X.Y.Z.jar)
    glob_patterns = [
        (Path('/tmp'), 'tika-server*.jar'),
        (Path.home() / '.tika', 'tika-server*.jar'),
        (Path('/var/folders'), '**/tika-server*.jar'),  # macOS temp
    ]

    for base_path, pattern in glob_patterns:
        if base_path.exists():
            try:
                for found_path in base_path.glob(pattern):
                    if found_path.exists() and found_path.is_file():
                        logger.debug(f"Tika JAR found via glob: {found_path}")
                        return True, found_path
            except (PermissionError, OSError):
                continue

    return False, None


def check_tika_available() -> dict:
    """
    Comprehensive Tika availability check.

    Returns:
        Dictionary with status information
    """
    status = {
        'java_installed': False,
        'java_version': None,
        'tika_jar_available': False,
        'tika_jar_path': None,
        'can_use_tika': False,
        'issues': []
    }

    # Check Java
    java_installed, java_version = check_java_installed()
    status['java_installed'] = java_installed
    status['java_version'] = java_version

    if not java_installed:
        status['issues'].append('Java not installed (required for Tika)')

    # Check Tika JAR
    jar_available, jar_path = check_tika_jar_available()
    status['tika_jar_available'] = jar_available
    status['tika_jar_path'] = jar_path

    if not jar_available:
        status['issues'].append('Tika JAR not downloaded')

    # Can use Tika only if both are available
    status['can_use_tika'] = java_installed and jar_available

    return status


def prompt_tika_installation() -> bool:
    """
    Prompt user to install Tika.

    Returns:
        True if user wants to install, False otherwise
    """
    print("\n" + "="*80)
    print("⚠️  TIKA NOT AVAILABLE")
    print("="*80)

    status = check_tika_available()

    if not status['java_installed']:
        print("\n❌ Java is not installed (required for Apache Tika)")
        print("\nTo install Java:")
        print("  macOS:   brew install openjdk")
        print("  Ubuntu:  sudo apt install default-jre")
        print("  Windows: Download from https://adoptium.net/")
        print("\nWithout Tika, only text and code files will be processed.")
        print("(PDF, DOCX, XLSX, etc. will be skipped)")

    elif not status['tika_jar_available']:
        print("\n⚠️  Java is installed but Tika JAR not downloaded")
        print("\nTika enables processing of:")
        print("  • PDF documents")
        print("  • Microsoft Office (DOCX, XLSX, PPTX)")
        print("  • OpenOffice/LibreOffice formats")
        print("  • And 1000+ other formats")
        print("\nWithout Tika, only text and code files will be processed.")

    print("\n" + "-"*80)

    if not status['java_installed']:
        print("\n⚠️  Please install Java first, then re-run ragify")
        return False

    # Java is installed, ask about downloading Tika
    while True:
        response = input("\nDownload Apache Tika now? (~60MB) [y/N]: ").strip().lower()

        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            print("\n✓ Continuing without Tika (text/code files only)")
            return False
        else:
            print("Please answer 'y' or 'n'")


def download_tika() -> bool:
    """
    Download Tika JAR file.

    Returns:
        True if successful, False otherwise
    """
    try:
        print("\n📥 Downloading Apache Tika...")
        print("(This will take a few minutes)")

        # Import tika to trigger download
        from tika import parser as tika_parser

        # Trigger download by parsing a dummy file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            tika_parser.from_file(temp_path, requestOptions={'timeout': 300})
            os.unlink(temp_path)
            print("✅ Tika downloaded successfully!")
            return True
        except Exception as e:
            os.unlink(temp_path)
            print(f"❌ Tika download failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Failed to download Tika: {e}")
        return False


def ensure_tika_ready(interactive: bool = True, auto_skip: bool = False) -> bool:
    """
    Ensure Tika is ready to use, with user interaction.

    Args:
        interactive: If True, prompt user for installation
        auto_skip: If True, automatically skip Tika without prompting

    Returns:
        True if Tika is available, False if should continue without Tika
    """
    status = check_tika_available()

    # Already available
    if status['can_use_tika']:
        logger.info("✅ Apache Tika is available")
        return True

    # Auto-skip mode
    if auto_skip:
        logger.info("Skipping Tika (--no-tika flag)")
        return False

    # Non-interactive mode
    if not interactive:
        logger.warning("Tika not available in non-interactive mode")
        return False

    # Interactive mode: ask user
    if prompt_tika_installation():
        # User wants to download
        success = download_tika()
        if success:
            # Verify it's now available
            new_status = check_tika_available()
            return new_status['can_use_tika']
        else:
            print("\n⚠️  Download failed. Continuing without Tika.")
            return False
    else:
        # User doesn't want to download
        return False


def is_tika_available() -> bool:
    """
    Check if Tika is available for use.

    First checks via check_tika_available(), then falls back to trying
    tika-python directly in case the JAR is in an unexpected location.

    Returns:
        True if Tika can be used, False otherwise.
    """
    # First try standard check
    status = check_tika_available()
    if status['can_use_tika']:
        return True

    # Fallback: try tika-python directly (it knows its own JAR location)
    if status['java_installed']:
        try:
            from tika import tika
            # Check if tika-python has a valid JAR path
            jar_path = getattr(tika, 'TikaJarPath', None)
            if jar_path and Path(jar_path).exists():
                logger.info(f"Tika JAR found via tika-python: {jar_path}")
                return True
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Tika-python fallback check failed: {e}")

    return False


def print_tika_status():
    """Print detailed Tika status for debugging."""
    status = check_tika_available()

    print("\n=== Tika Status ===")
    print(f"Java installed: {status['java_installed']}")
    if status['java_version']:
        print(f"Java version: {status['java_version']}")
    print(f"Tika JAR available: {status['tika_jar_available']}")
    if status['tika_jar_path']:
        print(f"Tika JAR path: {status['tika_jar_path']}")
    print(f"Can use Tika: {status['can_use_tika']}")

    if status['issues']:
        print("\nIssues:")
        for issue in status['issues']:
            print(f"  - {issue}")
    print("="*20)