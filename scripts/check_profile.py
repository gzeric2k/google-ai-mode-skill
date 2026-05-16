import json
from pathlib import Path
import os, sys

if sys.platform == "win32":
    profile = (
        Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        / "google-ai-mode-skill"
        / "chrome_profile"
    )
else:
    profile = Path.home() / ".cache" / "google-ai-mode-skill" / "chrome_profile"

print(f"Profile: {profile}")
print(f"Profile exists: {profile.exists()}")

cookies_file = profile / "Default" / "Cookies"
print(f"Cookies file: {cookies_file.exists()}")

local_state = profile / "Local State"
if local_state.exists():
    data = json.loads(local_state.read_text(encoding="utf-8"))
    info = data.get("profile", {}).get("info_cache", {})
    print(f"Profiles in Local State: {list(info.keys())}")
    for k, v in info.items():
        print(
            f"  {k}: name={v.get('name', '?')}, email={v.get('user_name', '?')}, gaia={v.get('gaia_id', '?')[:10] if v.get('gaia_id') else 'None'}..."
        )
else:
    print("Local State not found")
