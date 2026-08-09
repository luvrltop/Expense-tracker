import csv
import os
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

def get_all_incomes(month, year):
    incomes, _ = load_items(month, year)
    return incomes

def get_all_expenses(month, year):
    _, expenses = load_items(month, year)
    return expenses

def parse_euro(value: str) -> float:
    v = value.replace("€", "").strip()
    
    v = v.replace(",", ".")
    try:
        return float(v)
    except:
        return 0.0

def sum_incomes(month, year):
    incomes = get_all_incomes(month, year)
    return sum(parse_euro(i.split()[0]) for i in incomes)

def sum_expenses(month, year):
    expenses = get_all_expenses(month, year)
    return sum(parse_euro(e.split()[0]) for e in expenses)

