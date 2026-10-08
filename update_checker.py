"""
update_checker.py
Checks the latest GitHub Release of the program. No GUI code in this file,
and no extra libraries are needed. Works for a public repository without a key.

Before each release:
  1. Raise APP_VERSION below.
  2. Build the exe and installer.
  3. On GitHub, create a Release whose tag matches (for example v1.2.0)
     and attach the installer .exe file to it.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

APP_NAME = "Accessible Video Transcriber"
APP_VERSION = "1.2.0"       # raise this for every release
GITHUB_OWNER = "ihrammal"
GITHUB_REPO = "video-transcriber"

API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
ISSUES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
CHECK_INTERVAL_SECONDS = 24 * 60 * 60  # automatic check at most once a day


def user_data_dir():
    """Writable per-user folder. Never write settings into Program Files."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _settings_path():
    return os.path.join(user_data_dir(), "update_settings.json")


def load_settings():
    settings = {"auto_check": True, "last_check": 0}
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            settings.update(json.load(f))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except OSError:
        pass


def set_auto_check(enabled):
    settings = load_settings()
    settings["auto_check"] = bool(enabled)
    save_settings(settings)


def should_auto_check():
    settings = load_settings()
    due = time.time() - settings["last_check"] >= CHECK_INTERVAL_SECONDS
    return bool(settings["auto_check"]) and due


def mark_checked():
    settings = load_settings()
    settings["last_check"] = time.time()
    save_settings(settings)


def parse_version(text):
    """'v1.2.3' becomes (1, 2, 3, 0) so versions compare correctly."""
    core = re.split(r"[-+ ]", text.strip().lstrip("vV"), maxsplit=1)[0]
    numbers = [int(n) for n in re.findall(r"\d+", core)]
    numbers += [0] * (4 - len(numbers))
    return tuple(numbers[:4])


def check_for_update():
    """
    Returns a dictionary:
      available, current, latest, notes, page_url, download_url
    Raises RuntimeError with a plain-language message if the check fails.
    """
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RuntimeError("No releases have been published yet.") from error
        if error.code == 403:
            raise RuntimeError(
                "GitHub is limiting requests right now. Please try again later."
            ) from error
        raise RuntimeError(f"GitHub returned error {error.code}.") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError(
            "Could not reach GitHub. Please check your internet connection."
        ) from error
    except ValueError as error:
        raise RuntimeError("GitHub sent a reply the program could not read.") from error

    tag = data.get("tag_name", "")
    download_url = ""
    for asset in data.get("assets", []):
        if asset.get("name", "").lower().endswith(".exe"):
            download_url = asset.get("browser_download_url", "")
            break

    return {
        "available": parse_version(tag) > parse_version(APP_VERSION),
        "current": APP_VERSION,
        "latest": tag.lstrip("vV") or "unknown",
        "notes": (data.get("body") or "").strip(),
        "page_url": data.get("html_url") or RELEASES_PAGE,
        "download_url": download_url,
    }
