import re
import requests
from packaging import version
from tkinter import messagebox
import webbrowser

# all releases (incl. pre-releases), /releases/latest would skip betas
RELEASES_API = "https://api.github.com/repos/luvrltop/Expense-tracker/releases?per_page=30"
RELEASES_PAGE = "https://github.com/luvrltop/Expense-tracker/releases"

def extract_version(tag):
    """'v5.6.7-beta1' -> '5.6.7-beta1', keeps the pre-release part so packaging compares it right
    (5.6.7-beta1 < 5.6.7-beta2 < 5.6.7). None if the tag has no version"""
    tag = tag.lower().lstrip("v")  # poistaa V tai v etuliitteen
    match = re.search(r'\d+\.\d+\.\d+(?:[-.]?(?:alpha|beta|rc|a|b)[-.]?\d*)?', tag)
    if not match:
        return None
    try:
        version.parse(match.group(0))
        return match.group(0)
    except version.InvalidVersion:
        return re.search(r'\d+\.\d+\.\d+', tag).group(0)

def is_prerelease(version_text):
    return version.parse(version_text).is_prerelease

def get_latest_release(current_version):
    """newest release on GitHub as {"version", "url"}, None if the check failed.
    Betas/alphas are only offered when the running version is a pre-release itself."""
    include_prereleases = is_prerelease(current_version)
    try:
        r = requests.get(RELEASES_API, timeout=5)
        """debug"""
        #print("STATUS:", r.status_code)
        #print("BODY:", r.text)

        if r.status_code != 200:
            return None

        best = None
        for release in r.json():
            if release.get("draft"):
                continue
            found = extract_version(release.get("tag_name", ""))
            if not found:
                continue
            # skip betas for normal users, whether github flags it or only the tag says so
            if not include_prereleases and (release.get("prerelease") or is_prerelease(found)):
                continue
            if best is None or version.parse(found) > version.parse(best["version"]):
                best = {"version": found, "url": release.get("html_url", RELEASES_PAGE)}

        return best or {"version": None, "url": RELEASES_PAGE}
    except Exception:
        return None

def is_newer(release, current_version):
    return bool(release and release["version"]) and version.parse(release["version"]) > version.parse(current_version)

def check_for_updates(current_version, show_popup=True, release=None):
    """returns the newer release or None. release can be passed in if it was already
    fetched (e.g. in a background thread)"""
    if release is None:
        release = get_latest_release(current_version)

    if not is_newer(release, current_version):
        return None

    if show_popup:
        if messagebox.askyesno(
            "Update available",
            f"Version {release['version']} is available.\n\nOpen download page?"
        ):
            webbrowser.open(release["url"])
    return release
