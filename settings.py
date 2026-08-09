import os
import csv
from datetime import datetime
from config import BASE_DIR

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.csv")
TIME_FILE = os.path.join(BASE_DIR, "total_time.txt")

def save_settings(month, year):
    with open(SETTINGS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([month, year])

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        #fallback if no settings.csv found
        current_month_text = datetime.now().strftime('%B') # February
        current_year_full = datetime.now().strftime('%Y')

        return current_month_text, current_year_full

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2:
                return row[0], row[1]

    return None, None

def load_total_time():
    try:
        with open(TIME_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_total_time(seconds):
    with open(TIME_FILE, "w") as f:
        f.write(str(seconds))
    