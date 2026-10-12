import csv
import os
import re
from config import BASE_DIR

def get_csv_path(month, year):
    filename = f"{year}_{month}.csv"
    return os.path.join(BASE_DIR, filename)


def save_income(value, month, year):
    path = get_csv_path(month, year)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["income", value])


def save_expense(value, month, year):
    path = get_csv_path(month, year)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["expense", value])

def load_items(month, year):
    path = get_csv_path(month, year)
    if not os.path.exists(path):
        return [], []

    incomes = []
    expenses = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2:
                t, val = row
                if t == "income":
                    incomes.append(val)
                elif t == "expense":
                    expenses.append(val)

    return incomes, expenses

def _read_rows(month, year):
    path = get_csv_path(month, year)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.reader(f))

def _write_rows(rows, month, year):
    with open(get_csv_path(month, year), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

def _kind_positions(rows, kind):
    """file row numbers of the "income"/"expense" rows, in the same order as load_items"""
    return [i for i, row in enumerate(rows) if len(row) == 2 and row[0] == kind]

def delete_item(kind, index, month, year):
    """delete the index:th row of kind, returns its text (None if not found)"""
    rows = _read_rows(month, year)
    positions = _kind_positions(rows, kind)
    if index >= len(positions):
        return None
    text = rows.pop(positions[index])[1]
    _write_rows(rows, month, year)
    return text

def insert_item(kind, index, text, month, year):
    """put a row back as the index:th row of kind (undo delete)"""
    rows = _read_rows(month, year)
    positions = _kind_positions(rows, kind)
    if index < len(positions):
        rows.insert(positions[index], [kind, text])
    else:
        rows.append([kind, text])
    _write_rows(rows, month, year)

def update_item(kind, index, text, month, year):
    """replace the text of the index:th row of kind"""
    rows = _read_rows(month, year)
    positions = _kind_positions(rows, kind)
    if index >= len(positions):
        return False
    rows[positions[index]] = [kind, text]
    _write_rows(rows, month, year)
    return True

def get_years_with_data():
    """years that have at least one {year}_{month}.csv file"""
    years = set()
    for name in os.listdir(BASE_DIR):
        match = re.match(r"^(\d{4})_\w+\.csv$", name)
        if match:
            years.add(int(match.group(1)))
    return years

def get_stats():
    """(months with entries, income entries, expense entries) over all csv files"""
    months = incomes = expenses = 0
    for name in os.listdir(BASE_DIR):
        match = re.match(r"^(\d{4})_(\w+)\.csv$", name)
        if not match:
            continue
        month_incomes, month_expenses = load_items(match.group(2), match.group(1))
        if month_incomes or month_expenses:
            months += 1
        incomes += len(month_incomes)
        expenses += len(month_expenses)
    return months, incomes, expenses

def get_all_incomes(month, year):
    incomes, _ = load_items(month, year)
    return incomes

def get_all_expenses(month, year):
    _, expenses = load_items(month, year)
    return expenses

def parse_amount(value: str):
    """amount token ("12,50€", "12.5") to float, None if it isn't a number"""
    v = value.replace("€", "").strip().replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None

def parse_euro(value: str) -> float:
    amount = parse_amount(value)
    return 0.0 if amount is None else amount

def split_entry(text):
    """'12,50€ note' -> (12.5, 'note'), amount is None if the first token isn't a number"""
    parts = text.split(maxsplit=1)
    if not parts:
        return None, ""
    amount = parse_amount(parts[0])
    if amount is None:
        return None, text
    return amount, parts[1] if len(parts) > 1 else ""

def sum_incomes(month, year):
    incomes = get_all_incomes(month, year)
    return sum(split_entry(i)[0] or 0.0 for i in incomes)

def sum_expenses(month, year):
    expenses = get_all_expenses(month, year)
    return sum(split_entry(e)[0] or 0.0 for e in expenses)

