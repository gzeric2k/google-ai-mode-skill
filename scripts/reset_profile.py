#!/usr/bin/env python3
"""
Reset Browser Profile - Fix Language Issues

Deletes the persistent browser profile to force fresh creation with English settings.
Use this if Google still shows German interface after language fixes.

Usage:
    python scripts/run.py reset_profile.py
"""

import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import BROWSER_PROFILE_DIR


def main():
    print("=" * 60)
    print("BROWSER PROFILE RESET")
    print("=" * 60)
    print()

    if BROWSER_PROFILE_DIR.exists():
        print(f"📁 Profile location: {BROWSER_PROFILE_DIR}")
        print(f"⚠️  This will delete all browser data:")
        print(f"   - Cached language settings (fixes German interface)")
        print(f"   - Cookies and session (may trigger CAPTCHA on next search)")
        print(f"   - Login state")
        print()

        response = input("Continue? (y/N): ").strip().lower()
        if response != "y":
            print("❌ Cancelled.")
            return 1

        print()
        print(f"🗑️  Deleting profile...")
        shutil.rmtree(BROWSER_PROFILE_DIR)
        print(f"✅ Profile deleted!")
        print()
        print(f"📝 Next steps:")
        print(f"   1. Run a search:")
        print(f"      python scripts/run.py search.py --query 'test' --save --debug")
        print(f"   2. Profile will be recreated with English settings")
        print()
        return 0
    else:
        print(f"ℹ️  No profile found at: {BROWSER_PROFILE_DIR}")
        print(f"   Profile will be created on first search.")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
