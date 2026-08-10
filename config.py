import os

VERSION = "1.0.0"
version_from_config = VERSION
APP_NAME = "Expense-Tracker"
WINDOW_TITLE = f"{APP_NAME} {VERSION}"
main_window_title = WINDOW_TITLE

BASE_DIR = os.path.join(os.environ.get("APPDATA"), APP_NAME)
os.makedirs(BASE_DIR, exist_ok=True)
