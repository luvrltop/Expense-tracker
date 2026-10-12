import os
import csv
from datetime import datetime
from config import BASE_DIR

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.csv")
TIME_FILE = os.path.join(BASE_DIR, "total_time.txt")

def save_settings(month, year, theme, amounts_hidden=False, hide_lists=False):
    with open(SETTINGS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([month, year, theme, int(amounts_hidden), int(hide_lists)])

def load_settings():
    """returns month, year, theme, amounts_hidden, hide_lists"""
    if not os.path.exists(SETTINGS_FILE):
        #fallback if no settings.csv found
        current_month_text = datetime.now().strftime('%B') # February
        current_year_full = datetime.now().strftime('%Y')
        default_theme = "expensetrackerlight"

        return current_month_text, current_year_full, default_theme, False, False

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            # older versions saved fewer columns, missing flags default to False
            if 3 <= len(row) <= 5:
                flags = [value == "1" for value in row[3:]] + [False] * (5 - len(row))
                return row[0], row[1], row[2], flags[0], flags[1]

    return None, None, None, False, False

def load_total_time():
    try:
        with open(TIME_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_total_time(seconds):
    with open(TIME_FILE, "w") as f:
        f.write(str(seconds))
