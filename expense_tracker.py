#pyinstaller --onefile --windowed --hidden-import=ttkbootstrap --hidden-import=ttkbootstrap.constants expense_tracker.py

import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from settings import load_settings, save_settings, save_total_time, load_total_time
from storage import load_items, save_income, save_expense, get_all_incomes, get_all_expenses, parse_euro, sum_expenses, sum_incomes
from config import main_window_title, version_from_config
import time

start_time = time.time()
DARKSYMBOL = "⏾"
LIGHTSYMBOL = "☀︎"
DARKTHEME = "expensetrackerdark"
LIGHTTHEME = "expensetrackerlight"
#WINDOW_TITLE = appname()
last_month, last_year, last_theme = load_settings()

def change_theme():
    
    current_theme = main_window.style.theme_use()

    if current_theme == DARKTHEME:
        main_window.style.theme_use(LIGHTTHEME)
        theme_button.config(text=DARKSYMBOL)
    else:
        main_window.style.theme_use(DARKTHEME)
        theme_button.config(text=LIGHTSYMBOL)
    


def normalize_euro(value: str) -> str:
    v = value.strip()


    num = ""
    rest = ""

    for i, ch in enumerate(v):
        if ch.isdigit() or ch in ",.":
            num += ch
        else:
            rest = v[i:]
            break

    # no num, return original --> user warning in future?
    if not num:
        return v

    # delete possible unit symbols
    rest = rest.lstrip()
    if rest.lower().startswith(("e", "eur", "€")):
        
        if rest.lower().startswith("eur"):
            rest = rest[3:].lstrip()
        else:
            rest = rest[1:].lstrip()

    # add € after last number
    num = num.rstrip("€") + "€"

    return f"{num} {rest}".strip()



def add_income(event):
    raw = income_entry.get().strip()
    if raw and raw != "add income, note(optional)":
        value = normalize_euro(raw)
        tk.Label(income_list, text=value).pack(anchor="w")
        sep = tk.Frame(income_list)
        sep.pack(fill="x", pady=(2,5))
        tb.Separator(sep, orient=HORIZONTAL).pack(fill="x")

        save_income(value, month_var.get(), year_var.get())
        income_entry.delete(0, "end")
        #income_entry.insert(0, "add income, note(optional)")
    refresh_lists()



def add_expense(event):
    raw = expense_entry.get().strip()
    if raw and raw != "add expense, note(optional)":
        value = normalize_euro(raw)
        tk.Label(expense_list, text=value).pack(anchor="w")
        sep = tk.Frame(expense_list)
        sep.pack(fill="x", pady=(2,5))
        tb.Separator(sep, orient=HORIZONTAL).pack(fill="x")

        save_expense(value, month_var.get(), year_var.get())
        expense_entry.delete(0, "end")
        
        #expense_entry.insert(0, "add expense, note(optional)")
    refresh_lists()



def refresh_lists(*args):
    month = month_var.get()
    year = year_var.get()

    incomes, expenses = load_items(month, year)

    # empty gui lists
    for w in income_list.winfo_children():
        w.destroy()
    for w in expense_list.winfo_children():
        w.destroy()

    # refill
    for inc in incomes:
        tk.Label(income_list, text=inc).pack(anchor="w")
        sep = tk.Frame(income_list)
        sep.pack(fill="x", pady=(2,5))
        tb.Separator(sep, orient=HORIZONTAL).pack(fill="x")

    for exp in expenses:
        tk.Label(expense_list, text=exp).pack(anchor="w")
        sep = tk.Frame(expense_list)
        sep.pack(fill="x", pady=(2,5))
        tb.Separator(sep, orient=HORIZONTAL).pack(fill="x")


    total_income = sum_incomes(month, year)
    total_expense = sum_expenses(month, year)
    remaining_money = total_income - total_expense

    if total_income > 0:
        used_percent = round((total_expense / total_income) * 100, 1)
    else:
        used_percent = 0
    all_income.config(text=f"All income (+): {total_income}€")
    all_expense.config(text=f"All expenses (-): {total_expense}€")

    total_amount.config(text=f"Remaining budget: {remaining_money}€")
    amount_of_budget_used.config(text=f"Budget used: {used_percent}%")

def set_dynamic_info_minsize(window, margin_x=40, margin_y=80):
    window.update_idletasks()

    req_width = window.winfo_reqwidth()
    req_height = window.winfo_reqheight()

    max_width = window.winfo_screenwidth() - margin_x
    max_height = window.winfo_screenheight() - margin_y

    width = min(req_width, max_width)
    height = min(req_height, max_height)

    window.geometry(f"{width}x{height}")
    window.minsize(width, height)

def open_info_window():
    info_win = tk.Toplevel(main_window)
    info_win.title("Usage info")
    #info_win.geometry("300x200")
    info_win.resizable(True, True)

    #infoheader
    infoheader_frame = tk.Frame(info_win, borderwidth=5, relief="raised")
    infoheader_frame.pack(fill="both", expand=False, padx=30, pady=(20, 10), anchor="s")
    infoheader = tk.Label(infoheader_frame, text="Usage info", font=("Arial", 14))
    infoheader.pack(padx=10, pady=10)

    #mainframe
    info_frame = tk.Frame(info_win, borderwidth=5, relief="raised")
    info_frame.pack(fill="both", expand=True, padx=30, pady=(20, 40), anchor="center")

    #version label
    version_label = tk.Label(info_frame, text=f"Current version: {version_from_config}", font=("Arial", 12))
    version_label.pack(pady=10, padx=(5,10), anchor="w")
    # session time label
    session_label = tk.Label(info_frame, text="Session: 00h 00min 00s", font=("Arial", 12))
    session_label.pack(pady=10, padx=(5,10), anchor="w")

    # total time label
    total_label = tk.Label(info_frame, text="Total time: 00h 00min 00s", font=("Arial", 12))
    total_label.pack(pady=10, padx=(5,10), anchor="w")

    # --- UPDATE SESSION TIME ---
    def update_session():
        global elapsed
        elapsed = int(time.time() - start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        session_label.config(text=f"Session: {hours}h {minutes}min {seconds}s")
        info_win.after(1000, update_session)

    update_session()
    set_dynamic_info_minsize(info_win)


    
    def update_total():
        total_loaded = load_total_time()
        total_added = total_loaded + elapsed
        hours = total_added // 3600
        minutes = (total_added % 3600) // 60
        seconds = total_added % 60
        total_label.config(text=f"Total time: {hours}h {minutes}min {seconds}s")
        info_win.after(1000, update_total)

    update_total()


def on_close():
    current_theme = main_window.style.theme_use()

    save_settings(month_var.get(), year_var.get(), current_theme)

    session_seconds = int(time.time()-start_time)

    total_time = load_total_time()

    new_total = total_time + session_seconds

    save_total_time(new_total)

    main_window.destroy()

# make list scrollable
def make_scrollable_list(parent, bootstyle):
    selected_bootstyle = bootstyle
    canvas = tk.Canvas(parent, height=150, highlightthickness=0)
    scrollbar = tb.Scrollbar(parent, orient="vertical", command=canvas.yview, bootstyle=selected_bootstyle)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    list_frame = tk.Frame(canvas)

    #bind canvas width to list_frame width
    def resize_list_frame(event):
        canvas.itemconfig(window_id, width=event.width)

    window_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")

    canvas.bind("<Configure>", resize_list_frame)

    def update_scroll(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    list_frame.bind("<Configure>", update_scroll)

    return list_frame

def set_dynamic_minsize(window, margin_x=40, margin_y=80):
    window.update_idletasks()

    measured_width = max(window.winfo_reqwidth(), window.winfo_width())
    measured_height = max(window.winfo_reqheight(), window.winfo_height())

    max_width = max(1, window.winfo_screenwidth() - margin_x)
    max_height = max(1, window.winfo_screenheight() - margin_y)

    window.minsize(
        min(measured_width, max_width),
        min(measured_height, max_height),
    )



# MAIN window
main_window = tb.Window(title=main_window_title, themename=last_theme)

#main_window.minsize(700,870)

main_window.resizable(True, True)

if last_theme == DARKTHEME:
    theme_symbol = LIGHTSYMBOL
else:
    theme_symbol = DARKSYMBOL

theme_button = tb.Button(main_window, text=theme_symbol, bootstyle="info-link", command=lambda: change_theme())
theme_button.place(relx=0, x=5, y=5, anchor="nw")
info_button = tb.Button(main_window, text="[i]", bootstyle="info-link", command=lambda: open_info_window())
info_button.place(relx=1.0, x=-5, y=5, anchor="ne")


# HEADER text
header_frame = tk.Frame(main_window, borderwidth=5, relief="raised")
header_frame.pack(pady=20)

header_text = tk.Label(header_frame, text="Expense tracker", font="Arial, 23")
header_text.pack(fill="both", pady=(10, 10), padx=10)

# month/year selection menu
top_selection_bar = tk.Frame(main_window)
top_selection_bar.pack(fill="x", pady=0)

top_selection_bar.columnconfigure(0, weight=1)
top_selection_bar.columnconfigure(6, weight=1)

# MONTH LABEL
month_label = tk.Label(top_selection_bar, text="Month:")
month_label.grid(row=0, column=1, sticky="e", padx=2, pady=0)

# MONTH COMBO
month_var = tk.StringVar()

month_box = tb.Combobox(top_selection_bar, textvariable=month_var,
                        values=["January","February","March","April","May","June",
                                "July","August","September","October","November","December"],
                        width=12)
month_box.grid(row=0, column=2, sticky="w", padx=4, pady=0)
month_box.current(0)

# SEPARATOR vertical
separatorvert = tb.Separator(top_selection_bar, orient=VERTICAL)
separatorvert.grid(row=0, column=3, sticky="ns", padx=6, pady=0)

# YEAR LABEL
year_label = tk.Label(top_selection_bar, text="Year:")
year_label.grid(row=0, column=4, sticky="e", padx=2, pady=0)

# YEAR COMBO
year_var = tk.StringVar()

year_box = tb.Combobox(top_selection_bar, textvariable=year_var,
                       values=["2024","2025","2026","2027","2028"],
                       width=8)
year_box.grid(row=0, column=5, sticky="w", padx=4, pady=0)
year_box.current(2)


if last_month:
    month_var.set(last_month)
month_var.trace_add("write", refresh_lists)
if last_year:
    year_var.set(last_year)
year_var.trace_add("write", refresh_lists)


# MAIN CONTENT FRAME
main_frame = tk.Frame(main_window, borderwidth=5, relief="raised")
main_frame.pack(fill="both", expand=True, padx=70, pady=(20, 40))

# inner CONTENT FRAME ---
content_frame = tk.Frame(main_frame)
content_frame.pack(fill="both", expand=True)

# THREE SECTIONS
income_frame = tk.Frame(content_frame, padx=5, pady=5)

expense_frame = tk.Frame(content_frame, padx=5, pady=5)
total_frame = tk.Frame(content_frame, padx=0, pady=5)

income_frame.pack(fill="x", pady=10)

expense_frame.pack(fill="x", pady=10)

separator1 = tb.Separator(content_frame, orient=HORIZONTAL)
separator1.pack(fill=X, pady=5)

total_frame.pack(fill="x", pady=10)

# income
tk.Label(income_frame, text="Income (+)", font=("Arial", 14)).pack(anchor="w")

income_inner = tk.Frame(income_frame)
income_inner.pack(fill="both", expand=True)

# incom frame list
income_list_frame = tk.Frame(income_inner, borderwidth=5, relief="sunken")
income_list_frame.pack(fill="both", expand=True, side="top", pady=0)

income_list = make_scrollable_list(income_list_frame, "success-round")


# incom entry frame
income_entry_frame = tk.Frame(income_inner)
income_entry_frame.pack(fill="x", side="bottom")

income_entry = tk.Entry(income_entry_frame, justify="left")
income_entry.insert(0, "add income, note(optional)")
income_entry.pack(fill="x", pady=(10, 0))


def income_focus_in(event):
    if income_entry.get() == "add income, note(optional)":
        income_entry.delete(0, "end")

def income_focus_out(event):
    if income_entry.get().strip() == "":
        income_entry.insert(0, "add income, note(optional)")



income_entry.bind("<FocusIn>", income_focus_in)
income_entry.bind("<FocusOut>", income_focus_out)
income_entry.bind("<Return>", add_income)



# EXPENSE SECTION 
tk.Label(expense_frame, text="Expense (-)", font=("Arial", 14)).pack(anchor="w")

expense_inner = tk.Frame(expense_frame)
expense_inner.pack(fill="both", expand=True)

expense_list_frame = tk.Frame(expense_inner, borderwidth=5, relief="sunken")
expense_list_frame.pack(fill="both", expand=True, side="top")

expense_list = make_scrollable_list(expense_list_frame, "danger-round")

expense_entry_frame = tk.Frame(expense_inner)
expense_entry_frame.pack(fill="x", side="bottom")

expense_entry = tk.Entry(expense_entry_frame, justify="left")
expense_entry.insert(0, "add expense, note(optional)")
expense_entry.pack(fill="x", pady=(10, 0))

def expense_focus_in(event):
    if expense_entry.get() == "add expense, note(optional)":
        expense_entry.delete(0, "end")

def expense_focus_out(event):
    if expense_entry.get().strip() == "":
        expense_entry.insert(0, "add expense, note(optional)")



expense_entry.bind("<FocusIn>", expense_focus_in)
expense_entry.bind("<FocusOut>", expense_focus_out)
expense_entry.bind("<Return>", add_expense)



# TOTAL SECTION 

# All income + All expenses
row1 = tk.Frame(total_frame)
row1.pack(fill="x", pady=(0,20))

all_income = tk.Label(row1, text="All income: 0€", font=("Arial", 14), anchor="w")
all_income.pack(side="left", padx=10)

all_expense = tk.Label(row1, text="All expenses: 0€", font=("Arial", 14), anchor="w")
all_expense.pack(side="left", padx=10)

lower_separator = tb.Separator(total_frame, orient=HORIZONTAL).pack(fill=X)
#  Remaining budget + Budget used
row2 = tk.Frame(total_frame)
row2.pack(fill="x", pady=(20,10))

total_amount = tk.Label(row2, text="Remaining budget: 0€", font=("Arial", 14), anchor="w")
total_amount.pack(side="left", padx=10)

amount_of_budget_used = tk.Label(row2, text="Budget used: 0%", font=("Arial", 14), anchor="w")
amount_of_budget_used.pack(side="left", padx=10)

main_window.protocol("WM_DELETE_WINDOW", on_close)
# MAINLOOP
refresh_lists()
set_dynamic_minsize(main_window)
main_window.mainloop()

