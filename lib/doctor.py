"""
System prerequisites checker for ragify.

Verifies that all required components are installed and running:
- Python 3.10+
- Python dependencies
- Java (for Apache Tika)
- Ollama with nomic-embed-text model
- Qdrant vector database
- Disk space
"""

import os
import subprocess
import shutil
import sys
from typing import List, Tuple

import requests


def run_doctor_checks(fix: bool = False) -> None:
    """Run system prerequisite checks for ragify."""
    print("=" * 80)
    print("🩺 RAGIFY DOCTOR - System Prerequisites Check")
    print("=" * 80)
    print()

    checks = []
    issues = []

    # 1. Check Python version
    print("🐍 Checking Python version...")
    python_version = sys.version_info
    if python_version >= (3, 10):
        print(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        checks.append(('Python 3.10+', True))
    else:
        print(f"   ❌ Python {python_version.major}.{python_version.minor}.{python_version.micro} (requires 3.10+)")
        checks.append(('Python 3.10+', False))
        issues.append("Upgrade Python to 3.10 or higher")
    print()

    # 2. Check Python dependencies
    print("📦 Checking Python dependencies...")
    required_packages = ['requests', 'beautifulsoup4', 'chonkie', 'semchunk', 'tiktoken',
                         'tqdm', 'structlog', 'pydantic', 'qdrant-client', 'tika']
    missing_packages = []

    try:
        result = subprocess.run(['pip3', 'list'], capture_output=True, text=True, timeout=10)
        pip_list = result.stdout.lower()

        for pkg in required_packages:
            if pkg.lower() in pip_list or pkg.replace('-', '_').lower() in pip_list:
                print(f"   ✅ {pkg}")
            else:
                print(f"   ❌ {pkg} (missing)")
                missing_packages.append(pkg)

        if missing_packages:
            checks.append(('Python dependencies', False))
            issues.append(f"Install missing packages: pip3 install {' '.join(missing_packages)}")

            if fix:
                print(f"\n   🔧 Installing missing packages...")
                try:
                    subprocess.run(['pip3', 'install'] + missing_packages, check=True)
                    print(f"   ✅ Successfully installed missing packages")
                except subprocess.CalledProcessError as e:
                    print(f"   ❌ Failed to install packages: {e}")
        else:
            checks.append(('Python dependencies', True))
    except Exception as e:
        print(f"   ⚠️  Could not check dependencies: {e}")
        checks.append(('Python dependencies', False))
    print()

    # 3. Check Java (for Tika)
    print("☕ Checking Java (for Apache Tika)...")
    java_installed = shutil.which('java') is not None
    if java_installed:
        try:
            result = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=5)
            version_output = result.stderr.split('\n')[0] if result.stderr else 'unknown'
            print(f"   ✅ Java installed ({version_output})")
            checks.append(('Java', True))
        except Exception as e:
            print(f"   ⚠️  Java check failed: {e}")
            checks.append(('Java', False))
    else:
        print(f"   ❌ Java not found")
        checks.append(('Java', False))
        issues.append("Install Java 8+ for Apache Tika support")
        issues.append("Alternative: use --no-tika flag to skip Tika-based extraction")
    print()

    # 4. Check Ollama
    print("🦙 Checking Ollama...")
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Ollama running at {ollama_url}")
            checks.append(('Ollama running', True))

            # Check for nomic-embed-text model
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            if any('nomic-embed-text' in name for name in model_names):
                print(f"   ✅ nomic-embed-text model available")
                checks.append(('nomic-embed-text model', True))
            else:
                print(f"   ❌ nomic-embed-text model not found")
                checks.append(('nomic-embed-text model', False))
                issues.append("Pull model: ollama pull nomic-embed-text")
        else:
            print(f"   ❌ Ollama responded with status {response.status_code}")
            checks.append(('Ollama running', False))
            issues.append("Start Ollama: ollama serve")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to Ollama at {ollama_url}")
        checks.append(('Ollama running', False))
        issues.append("Start Ollama: ollama serve")
    except Exception as e:
        print(f"   ⚠️  Ollama check failed: {e}")
        checks.append(('Ollama running', False))
    print()

    # 5. Check Qdrant
    print("🗄️  Checking Qdrant...")
    qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
    try:
        response = requests.get(f"{qdrant_url}/", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Qdrant running at {qdrant_url}")
            checks.append(('Qdrant running', True))

            # Get collections count
            try:
                collections_response = requests.get(f"{qdrant_url}/collections", timeout=5)
                if collections_response.status_code == 200:
                    collections = collections_response.json().get('result', {}).get('collections', [])
                    print(f"   ℹ️  Collections: {len(collections)}")
            except:
                pass
        else:
            print(f"   ❌ Qdrant responded with status {response.status_code}")
            checks.append(('Qdrant running', False))
            issues.append("Start Qdrant: docker run -p 6333:6333 qdrant/qdrant")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to Qdrant at {qdrant_url}")
        checks.append(('Qdrant running', False))
        issues.append("Start Qdrant: docker run -p 6333:6333 qdrant/qdrant")
    except Exception as e:
        print(f"   ⚠️  Qdrant check failed: {e}")
        checks.append(('Qdrant running', False))
    print()

    # 6. Check disk space
    print("💾 Checking disk space...")
    try:
        stat = os.statvfs('/')
        free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if free_space_gb >= 5.0:
            print(f"   ✅ Available: {free_space_gb:.1f} GB")
            checks.append(('Disk space (5GB+)', True))
        else:
            print(f"   ⚠️  Only {free_space_gb:.1f} GB available (recommended: 5GB+)")
            checks.append(('Disk space (5GB+)', False))
            issues.append("Free up disk space (at least 5GB recommended)")
    except Exception as e:
        print(f"   ⚠️  Could not check disk space: {e}")
    print()

    # Summary
    print("=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, status in checks if status)
    total = len(checks)

    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")

    print()
    print(f"Result: {passed}/{total} checks passed")

    if issues:
        print()
        print("🔧 RECOMMENDED ACTIONS:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")

    print("=" * 80)

    if passed == total:
        print("✅ All checks passed! Ragify is ready to use.")
    else:
        print(f"⚠️  {total - passed} issue(s) found. Fix them before using ragify.")
