import os
import csv
from config import BASE_DIR

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.csv")

def save_settings(month, year):
    with open(SETTINGS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([month, year])

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return None, None

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2:
                return row[0], row[1]

    return None, None
