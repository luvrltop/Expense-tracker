import re
import requests
from packaging import version
from tkinter import messagebox
import webbrowser

REPO_URL = "https://api.github.com/repos/luvrltop/Expense-tracker/releases/latest"
RELEASE_PAGE = "https://github.com/luvrltop/Expense-tracker/releases/latest"

def extract_version(tag):
    tag = tag.lower().lstrip("v")  # poistaa V tai v etuliitteen
    match = re.search(r'(\d+\.\d+\.\d+)', tag)
    return match.group(1) if match else None

def get_latest_version():
    try:
        r = requests.get(REPO_URL, timeout=5)
        #print("TAG:", r.json()["tag_name"])
        #print("STATUS:", r.status_code)
        #print("BODY:", r.text)


        if r.status_code != 200:
            return None
        latest_tag = r.json().get("tag_name", "")


        return extract_version(latest_tag)
    except Exception:
        return None

def check_for_updates(current_version, show_popup=True):
    latest = get_latest_version()
    
    #print("Latest tag:", latest)

    if not latest:
        return None

    if version.parse(latest) > version.parse(current_version):
        if show_popup:
            if messagebox.askyesno(
                "Update available",
                f"Version {latest} is available.\n\nOpen download page?"
            ):
                webbrowser.open(RELEASE_PAGE)
        return latest


    return None
