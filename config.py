import os

VERSION = 1.0
WINDOW_TITLE = f"Expense tracker {VERSION}"

APP_NAME = "Expense-Tracker"
BASE_DIR = os.path.join(os.environ.get("APPDATA"), APP_NAME)
os.makedirs(BASE_DIR, exist_ok=True)
