#pyinstaller --onefile --windowed --icon=app.ico --hidden-import=ttkbootstrap --hidden-import=ttkbootstrap.constants --add-data "app.ico;." --add-data "help.txt;." expense_tracker.py

import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from settings import load_settings, save_settings, save_total_time, load_total_time
from ttkbootstrap.style import Colors
from widgets import StripedProgressBar
from storage import (load_items, save_income, save_expense, delete_item, insert_item, update_item,
                     get_years_with_data, get_stats, split_entry, sum_expenses, sum_incomes)
from config import main_window_title, version_from_config
from update_checker import check_for_updates, get_latest_release, is_newer, RELEASES_PAGE
from help_functions import resource_path, set_title_bar_colors
import time
import threading
import warnings
from PIL import Image, ImageTk
from datetime import datetime
import sys
import os

start_time = time.time()

DARKSYMBOL = "⏾"
LIGHTSYMBOL = "☀"  # no U+FE0E variation selector, Tk draws it as extra width
DARKTHEME = "expensetrackerdark"
LIGHTTHEME = "expensetrackerlight"
#WINDOW_TITLE = appname()
last_month, last_year, last_theme, last_amounts_hidden, last_hide_lists = load_settings()
HIDDEN_AMOUNT = "****"
UI_FONT = "Segoe UI"
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
AUTO_LOCK_MINUTES = 5
TOAST_MS = 5000
AMOUNT_WIDTH = 13  # chars, fits "1 000 000,00 €"


OUTLINE_BUTTON_STYLE = "App.secondary.Outline.TButton"


def mix_colors(color_a, color_b, amount):
    """blend two #rrggbb colors, amount 0 = a, 1 = b"""
    def to_rgb(color):
        h = color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    mixed = [round((1 - amount) * x + amount * y) for x, y in zip(to_rgb(color_a), to_rgb(color_b))]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def format_money(value):
    """finnish format: 1 000,50 € (no-break spaces so it never wraps)"""
    text = f"{abs(value):,.2f}".replace(",", " ").replace(".", ",")
    sign = "-" if round(value, 2) < 0 else ""
    return f"{sign}{text} €"


def run_app():

    # help function from todolist.py
    def resource_path(relative_path):
        """function for getting resource path"""
        try:
            base_path = sys._MEIPASS  # PyInstaller
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def change_theme():
        #eval curr theme
        current_theme = main_window.style.theme_use()

        if current_theme == DARKTHEME:
            main_window.style.theme_use(LIGHTTHEME)
            theme_button.config(text=DARKSYMBOL)
        else:
            main_window.style.theme_use(DARKTHEME)
            theme_button.config(text=LIGHTSYMBOL)
        apply_custom_styles()
        update_summary()  # progress bar colors come from the theme
        color_title_bar(main_window)
        if about["win"] is not None and about["win"].winfo_exists():
            color_title_bar(about["win"])

    def color_title_bar(window):
        """windows title bar in the theme colors (bg/fg), dark mode flag for the window buttons"""
        colors = main_window.style.colors
        dark = main_window.style.theme_use() == DARKTHEME
        set_title_bar_colors(window, colors.bg, colors.fg, dark)

    def apply_custom_styles():
        """own styles from current theme colors, ttk styles are per theme so rerun on theme change"""
        style = main_window.style
        colors = style.colors
        delete_red = Colors.update_hsv(colors.danger, vd=-0.2)
        # list rows (normal + hover)
        for prefix, bg in (("Row", colors.bg), ("RowHover", colors.active)):
            style.configure(f"{prefix}.TFrame", background=bg)
            style.configure(f"{prefix}.TLabel", background=bg, foreground=colors.fg)
            style.configure(f"{prefix}Delete.TLabel", background=bg, foreground=delete_red)
        # secondary texts (captions, hints, placeholders): theme secondary is too faint,
        # so use a blend that is clearly lighter than fg but still readable
        muted = mix_colors(colors.bg, colors.fg, 0.6)
        style.configure("Muted.TLabel", foreground=muted)
        style.configure("Empty.TLabel", background=colors.bg, foreground=muted)
        # grey hint text in the entry fields
        style.configure("Placeholder.TEntry", foreground=muted)
        # undo toast, inverted colors so it stands out
        style.configure("Toast.TFrame", background=colors.fg)
        style.configure("Toast.TLabel", background=colors.fg, foreground=colors.bg)
        style.configure("ToastUndo.TLabel", background=colors.fg, foreground=colors.primary)
        # outline buttons: theme secondary is too faint, so text = fg and border halfway bg -> fg.
        # child of secondary.Outline.TButton so it keeps that layout
        border = mix_colors(colors.bg, colors.fg, 0.45)
        style.configure(OUTLINE_BUTTON_STYLE, foreground=colors.fg, bordercolor=border, focuscolor=colors.fg)
        style.map(
            OUTLINE_BUTTON_STYLE,
            foreground=[("disabled", colors.secondary), ("pressed !disabled", colors.fg), ("hover !disabled", colors.fg)],
            background=[("pressed !disabled", border), ("hover !disabled", colors.active)],
            bordercolor=[("hover !disabled", colors.fg)],
            focuscolor=[("pressed !disabled", colors.fg), ("hover !disabled", colors.fg)],
            darkcolor=[("pressed !disabled", border), ("hover !disabled", colors.active)],
            lightcolor=[("pressed !disabled", border), ("hover !disabled", colors.active)],
        )
        # ttkbootstrap resets bootstyle widgets on theme change, so (re)assign the style
        for button in outline_buttons:
            button.configure(style=OUTLINE_BUTTON_STYLE)

    def persist_settings():
        save_settings(month_var.get(), year_var.get(), main_window.style.theme_use(),
                      amounts_hidden.get(), hide_lists.get())

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

        # no num, return original (rejected by validation in add_entry)
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

    # ENTRY FIELDS
    def setup_placeholder(entry, text):
        """grey hint text that disappears on focus"""
        def show(event=None):
            if not entry.get():
                entry.insert(0, text)
                entry.configure(style="Placeholder.TEntry")
                entry.placeholder_active = True

        def hide(event=None):
            if entry.placeholder_active:
                entry.delete(0, "end")
                entry.configure(style="TEntry")
                entry.placeholder_active = False

        entry.placeholder_active = False
        entry.bind("<FocusIn>", hide)
        entry.bind("<FocusOut>", show)
        show()

    def entry_value(entry):
        if getattr(entry, "placeholder_active", False):
            return ""
        return entry.get().strip()

    def flash_invalid(entry):
        """red border for a moment, the text stays so it can be fixed"""
        entry.configure(bootstyle="danger")

        def restore():
            if entry.winfo_exists():
                entry.configure(style="TEntry")
        entry.after(900, restore)

    def parse_input(raw):
        """returns the text to save, or None if it has no valid amount"""
        value = normalize_euro(raw)
        amount, _ = split_entry(value)
        return None if amount is None else value

    def add_entry(kind, entry):
        raw = entry_value(entry)
        if not raw:
            return
        value = parse_input(raw)
        if value is None:
            flash_invalid(entry)
            return
        save = save_income if kind == "income" else save_expense
        save(value, month_var.get(), year_var.get())
        entry.delete(0, "end")
        refresh_lists()

    # LIST ROWS
    def lists_masked():
        return amounts_hidden.get() and hide_lists.get()

    def display_amount(amount):
        if lists_masked():
            return HIDDEN_AMOUNT
        return "–" if amount is None else format_money(amount)

    def add_list_row(parent, kind, index, text):
        amount, note = split_entry(text)

        row = tb.Frame(parent, style="Row.TFrame")
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)
        # amount in its own right-aligned column, note next to it
        amount_label = tb.Label(row, text=display_amount(amount), style="Row.TLabel",
                                width=AMOUNT_WIDTH, anchor="e")
        amount_label.grid(row=0, column=0, padx=(2, 14))
        note_label = tb.Label(row, text=note, style="Row.TLabel", anchor="w")
        note_label.grid(row=0, column=1, sticky="ew")
        delete_label = tb.Label(row, text="✕", style="RowDelete.TLabel", padding=(4, 0), cursor="hand2")
        delete_label.grid(row=0, column=2, padx=(0, 5))
        delete_label.bind("<Button-1>", lambda e: delete_with_undo(kind, index, text))

        # highlight row under the cursor
        def set_hover(on):
            prefix = "RowHover" if on else "Row"
            row.configure(style=f"{prefix}.TFrame")
            amount_label.configure(style=f"{prefix}.TLabel")
            note_label.configure(style=f"{prefix}.TLabel")
            delete_label.configure(style=f"{prefix}Delete.TLabel")

        def on_leave(event):
            # <Leave> also fires when moving onto a child widget
            try:
                widget = main_window.winfo_containing(event.x_root, event.y_root)
            except KeyError:
                widget = None
            while widget is not None and widget is not row:
                widget = widget.master
            if widget is None:
                set_hover(False)

        labels = (amount_label, note_label, delete_label)
        for w in (row, amount_label, note_label):
            w.bind("<Double-Button-1>", lambda e: start_edit(row, labels, kind, index, text))
        for w in (row,) + labels:
            w.bind("<Enter>", lambda e: set_hover(True))
            w.bind("<Leave>", on_leave)

        sep = tb.Frame(parent)
        sep.pack(fill="x", pady=(2,5))
        tb.Separator(sep, orient=HORIZONTAL).pack(fill="x")

    def add_empty_state(parent, text):
        tb.Label(parent, text=text, style="Empty.TLabel", font=(UI_FONT, 10, "italic")).pack(pady=14)

    def start_edit(row, labels, kind, index, text):
        """double click: the row turns into an entry, Enter saves, Esc/click away cancels"""
        for w in labels:
            w.grid_remove()
        edit = tb.Entry(row, font=(UI_FONT, 10))
        edit.insert(0, text)
        edit.grid(row=0, column=0, columnspan=3, sticky="ew", padx=2, pady=2)
        edit.focus_set()
        edit.select_range(0, "end")
        month, year = month_var.get(), year_var.get()
        done = {"value": False}

        def finish(save):
            if done["value"]:
                return "break"
            if save:
                value = parse_input(edit.get().strip())
                if value is None:
                    flash_invalid(edit)
                    return "break"
                update_item(kind, index, value, month, year)
            done["value"] = True
            main_window.after_idle(refresh_lists)
            # "break" so Enter/Esc don't reach the window bindings (Esc = lock)
            return "break"

        edit.bind("<Return>", lambda e: finish(True))
        edit.bind("<Escape>", lambda e: finish(False))
        edit.bind("<FocusOut>", lambda e: finish(False))

    # DELETE + UNDO TOAST
    toast = {"frame": None, "after": None}

    def hide_toast():
        if toast["after"]:
            main_window.after_cancel(toast["after"])
            toast["after"] = None
        if toast["frame"] is not None:
            toast["frame"].destroy()
            toast["frame"] = None

    def show_toast(message, undo):
        hide_toast()
        frame = tb.Frame(main_window, style="Toast.TFrame", padding=(16, 8))
        tb.Label(frame, text=message, style="Toast.TLabel", font=(UI_FONT, 10)).pack(side="left")
        undo_label = tb.Label(frame, text="Undo", style="ToastUndo.TLabel", font=(UI_FONT, 10, "bold"),
                              cursor="hand2")
        undo_label.pack(side="left", padx=(18, 0))

        def on_undo(event):
            hide_toast()
            undo()
        undo_label.bind("<Button-1>", on_undo)

        frame.place(relx=0.5, rely=1.0, y=-14, anchor="s")
        frame.lift()
        toast["frame"] = frame
        toast["after"] = main_window.after(TOAST_MS, hide_toast)

    def delete_with_undo(kind, index, text):
        # remember where it was, undo puts it back even if the month was changed
        month, year = month_var.get(), year_var.get()
        if delete_item(kind, index, month, year) is None:
            return
        refresh_lists()

        amount, note = split_entry(text)
        shown = f"{display_amount(amount)} {note}".strip()

        def undo():
            insert_item(kind, index, text, month, year)
            refresh_lists()
        show_toast(f"Deleted: {shown}", undo)

    view = {"batch": False}

    def refresh_lists(*args):
        if view["batch"]:
            return
        month = month_var.get()
        year = year_var.get()
        incomes, expenses = load_items(month, year)

        # empty gui lists
        for w in income_list.winfo_children():
            w.destroy()
        for w in expense_list.winfo_children():
            w.destroy()

        # refill
        for i, inc in enumerate(incomes):
            add_list_row(income_list, "income", i, inc)
        if not incomes:
            add_empty_state(income_list, "No income yet")

        for i, exp in enumerate(expenses):
            add_list_row(expense_list, "expense", i, exp)
        if not expenses:
            add_empty_state(expense_list, "No expenses yet")

        update_summary()

    def format_euro(value):
        if amounts_hidden.get():
            return HIDDEN_AMOUNT
        return format_money(value)

    def update_summary():
        month = month_var.get()
        year = year_var.get()
        total_income = sum_incomes(month, year)
        total_expense = sum_expenses(month, year)
        remaining_money = round((total_income - total_expense), 2)

        if total_income > 0:
            used_percent = round((total_expense / total_income) * 100, 1)
        else:
            used_percent = 0

        all_income.config(text=format_euro(total_income))
        all_expense.config(text=format_euro(total_expense))
        total_amount.config(text=format_euro(remaining_money),
                            bootstyle="success" if remaining_money >= 0 else "danger")
        amount_of_budget_used.config(text=f"{used_percent:.1f} %".replace(".", ","))

        colors = main_window.style.colors
        if used_percent < 80:
            bar_color = colors.success
        elif used_percent < 100:
            bar_color = colors.warning
        else:
            bar_color = colors.danger
        budget_bar.set(used_percent, bar_color, trough_color=colors.active, bg=colors.bg)

    # MONTH NAVIGATION
    def year_values():
        now = datetime.now().year
        years = get_years_with_data() | {now - 1, now, now + 1}
        if year_var.get().isdigit():
            years.add(int(year_var.get()))
        return [str(y) for y in sorted(years)]

    def set_view(month, year):
        """change month and year with one refresh instead of two"""
        view["batch"] = True
        month_var.set(month)
        year_var.set(year)
        view["batch"] = False
        year_box.config(values=year_values())
        refresh_lists()

    def shift_month(delta):
        index = MONTHS.index(month_var.get()) + delta
        year = int(year_var.get()) + index // 12
        set_view(MONTHS[index % 12], str(year))

    # WELCOME / LOCK SCREEN
    welcome_state = {"shown": False}
    activity = {"last": time.time()}

    def mark_activity(event=None):
        activity["last"] = time.time()

    def lock_app(event=None):
        if not welcome_state["shown"]:
            show_welcome(locked=True)

    def check_idle():
        idle_seconds = time.time() - activity["last"]
        if not welcome_state["shown"] and idle_seconds > AUTO_LOCK_MINUTES * 60:
            lock_app()
        main_window.after(10_000, check_idle)

    def show_welcome(locked=False):
        """start screen that covers the whole window so money isn't visible right away.
        locked=True: same screen used as a lock (Esc, Lock button, idle), no loading"""
        welcome_state["shown"] = True
        hide_toast()
        welcome = tb.Frame(main_window)
        welcome.place(relx=0, rely=0, relwidth=1, relheight=1)
        welcome.lift()

        center = tb.Frame(welcome)
        center.place(relx=0.5, rely=0.45, anchor="center")

        hour = datetime.now().hour
        if hour < 5:
            greeting = "Good night"
        elif hour < 12:
            greeting = "Good morning"
        elif hour < 18:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        tb.Label(center, text=greeting, font=(UI_FONT, 16), style="Muted.TLabel").pack()
        clock_label = tb.Label(center, font=(UI_FONT, 64, "bold"))
        clock_label.pack(pady=(0, 0))
        date_label = tb.Label(center, font=(UI_FONT, 14), style="Muted.TLabel")
        date_label.pack(pady=(0, 30))

        tb.Separator(center, orient=HORIZONTAL).pack(fill="x", pady=(0, 20))
        tb.Label(center, text="Locked" if locked else "Opening", font=(UI_FONT, 10), style="Muted.TLabel").pack()
        tb.Label(center, text=f"{month_var.get()} {year_var.get()}", font=(UI_FONT, 20, "bold"),
                 bootstyle="primary").pack(pady=(0, 30))

        # loading: status text + percent, striped bar below (not when locking)
        if not locked:
            status_row = tb.Frame(center)
            status_row.pack(fill="x")
            status_label = tb.Label(status_row, text="", font=(UI_FONT, 10), style="Muted.TLabel")
            status_label.pack(side="left")
            percent_label = tb.Label(status_row, text="0%", font=(UI_FONT, 10, "bold"))
            percent_label.pack(side="right")
            loading_bar = StripedProgressBar(center, height=10)
            loading_bar.pack(fill="x", pady=(6, 30))

        # disabled until loading is done, so the layout doesn't jump
        continue_button = tb.Button(center, text="Continue", bootstyle="primary", padding=(40, 10),
                                    state="disabled", command=lambda: close_welcome())
        continue_button.pack()
        hint_label = tb.Label(center, text="", font=(UI_FONT, 9), style="Muted.TLabel")
        hint_label.pack(pady=(8, 0))

        tb.Label(welcome, text=main_window_title, font=(UI_FONT, 9), style="Muted.TLabel").place(
            relx=0.5, rely=1.0, y=-15, anchor="s")

        def update_clock():
            if not welcome.winfo_exists():
                return
            now = datetime.now()
            clock_label.config(text=now.strftime("%H:%M"))
            date_label.config(text=now.strftime("%A %d %B %Y"))
            welcome.after(1000, update_clock)

        def close_welcome():
            if not loading["ready"]:
                return
            main_window.unbind("<Return>")
            welcome.destroy()
            welcome_state["shown"] = False
            mark_activity()

        # LOADING STEPS
        # (text, percent when done, action). Real work runs in the action;
        # the bar eases toward the percent so each step is readable.
        def start_update_check():
            # network call in a thread so the window doesn't freeze
            def worker():
                loading["latest"] = get_latest_release(version_from_config)
            loading["thread"] = threading.Thread(target=worker, daemon=True)
            loading["thread"].start()

        steps = [
            ("Building interface", 25, None),
            (f"Loading {month_var.get()} {year_var.get()} entries", 60, refresh_lists),
            ("Checking for updates", 95, start_update_check),
            ("App is ready", 100, None),
        ]
        loading = {"step": -1, "shown": 0.0, "target": 0, "thread": None, "latest": None, "ready": False}

        def next_step():
            loading["step"] += 1
            text, percent, action = steps[loading["step"]]
            status_label.config(text=text if percent == 100 else f"{text}...")
            if action:
                action()
            loading["target"] = percent

        def set_ready():
            loading["ready"] = True
            if not locked:
                status_label.config(bootstyle="success")
            continue_button.config(state="normal")
            continue_button.focus_set()
            hint_label.config(text="or press Enter")
            if loading["latest"]:
                check_for_updates(version_from_config, show_popup=True, release=loading["latest"])

        def loading_tick():
            if not welcome.winfo_exists():
                return
            diff = loading["target"] - loading["shown"]
            if diff > 0:
                loading["shown"] = min(loading["target"], loading["shown"] + max(0.8, diff * 0.1))

            colors = main_window.style.colors
            bar_color = colors.success if loading["shown"] >= 100 else colors.primary
            loading_bar.set(loading["shown"], bar_color, trough_color=colors.active, bg=colors.bg)
            percent_label.config(text=f"{int(loading['shown'])}%")

            thread = loading["thread"]
            waiting = thread is not None and thread.is_alive()
            if loading["shown"] >= loading["target"] and not waiting:
                if loading["step"] < len(steps) - 1:
                    next_step()
                elif not loading["ready"]:
                    set_ready()
                    return
            welcome.after(16, loading_tick)

        update_clock()
        # bound on the window, removed on close so Enter in the entry fields isn't affected
        main_window.bind("<Return>", lambda e: close_welcome())
        if locked:
            set_ready()
        else:
            next_step()
            loading_tick()

    def toggle_amounts():
        amounts_hidden.set(not amounts_hidden.get())
        hide_button.config(text="Show amounts" if amounts_hidden.get() else "Hide amounts")
        persist_settings()
        refresh_lists()

    def on_hide_lists_changed():
        persist_settings()
        refresh_lists()

    # ABOUT WINDOW (layout modeled on the todolist app's About window)
    about = {"win": None}

    def format_duration(seconds):
        days, rest = divmod(int(seconds), 86400)
        hours, rest = divmod(rest, 3600)
        minutes, secs = divmod(rest, 60)
        if days:
            return f"{days}d {hours}h {minutes}min {secs}s"
        return f"{hours}h {minutes}min {secs}s"

    def load_logo(max_size):
        """app.ico as a PhotoImage (it is already bundled, so no extra data files needed)"""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # the ico has a non-square frame, PIL warns about it
                image = Image.open(resource_path("app.ico"))
                image.load()
            image = image.convert("RGBA")
            image.thumbnail(max_size)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def open_info_window():
        # only one About window, bring the old one up instead
        if about["win"] is not None and about["win"].winfo_exists():
            about["win"].deiconify()
            about["win"].lift()
            about["win"].focus_force()
            return

        info_win = tk.Toplevel(main_window)
        info_win.withdraw()  # built hidden, shown centered once ready (no flash, title bar can be colored)
        info_win.title("About")
        info_win.iconbitmap(resource_path("app.ico"))
        info_win.resizable(False, False)
        about["win"] = info_win

        notebook = tb.Notebook(info_win, bootstyle="primary")
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # INFO TAB
        info_tab = tb.Frame(notebook, padding=(40, 20))
        notebook.add(info_tab, text="Info")

        logo = load_logo((120, 120))
        if logo:
            logo_label = tb.Label(info_tab, image=logo)
            logo_label.image = logo  # keep a reference, tk doesn't
            logo_label.pack(pady=(0, 10))

        tb.Label(info_tab, text="Expense Tracker", font=(UI_FONT, 20, "bold")).pack()
        tb.Label(info_tab, text="Track your monthly income and expenses", font=(UI_FONT, 10),
                 style="Muted.TLabel").pack()

        tb.Label(info_tab, text=f"Version {version_from_config}", font=(UI_FONT, 12)).pack(pady=(24, 0))
        latest_label = tb.Label(info_tab, font=(UI_FONT, 10))
        status_label = tb.Label(info_tab, text="Checking for updates...", font=(UI_FONT, 10), style="Muted.TLabel")
        status_label.pack(pady=(2, 14))

        # releases list until the check finds the newest release, then that release's page
        release_url = {"url": RELEASES_PAGE}

        def open_github():
            import webbrowser
            webbrowser.open(release_url["url"])

        link = tb.Label(info_tab, text="Install new version", font=(UI_FONT, 10, "underline"),
                        bootstyle="primary", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: open_github())

        tb.Label(info_tab, text="© 2026 luvrltop", font=(UI_FONT, 8), style="Muted.TLabel").pack(pady=(24, 0))

        # update check in a thread so the window opens right away, result polled on the main thread
        update = {"done": False, "release": None}

        def worker():
            update["release"] = get_latest_release(version_from_config)
            update["done"] = True

        def poll_update():
            if not info_win.winfo_exists():
                return
            if not update["done"]:
                info_win.after(100, poll_update)
                return
            release = update["release"]
            if release is None:
                status_label.config(text="Update check failed", bootstyle="danger")
                return
            release_url["url"] = release["url"]
            if is_newer(release, version_from_config):
                latest_label.config(text=f"Latest version {release['version']}")
                latest_label.pack(before=status_label, pady=(2, 0))
                status_label.config(text="Update available", bootstyle="warning")
            else:
                status_label.config(text="Up to date", bootstyle="success")

        threading.Thread(target=worker, daemon=True).start()
        poll_update()

        # STATISTICS TAB
        stats_tab = tb.Frame(notebook, padding=(40, 20))
        notebook.add(stats_tab, text="Statistics")

        small_logo = load_logo((72, 72))
        if small_logo:
            small_logo_label = tb.Label(stats_tab, image=small_logo)
            small_logo_label.image = small_logo
            small_logo_label.pack(pady=(0, 6))
        tb.Label(stats_tab, text="Statistics", font=(UI_FONT, 20, "bold")).pack(pady=(0, 20))

        # label left, value right
        stats_grid = tb.Frame(stats_tab)
        stats_grid.pack(fill="x")
        stats_grid.columnconfigure(1, weight=1)

        def stat_row(row, caption):
            tb.Label(stats_grid, text=caption, font=(UI_FONT, 11), style="Muted.TLabel").grid(
                row=row, column=0, sticky="w", pady=4)
            value = tb.Label(stats_grid, font=(UI_FONT, 11, "bold"))
            value.grid(row=row, column=1, sticky="e", pady=4, padx=(30, 0))
            return value

        months_value = stat_row(0, "Months tracked")
        incomes_value = stat_row(1, "Income entries")
        expenses_value = stat_row(2, "Expense entries")
        tb.Separator(stats_grid, orient=HORIZONTAL).grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
        session_value = stat_row(4, "This session")
        total_value = stat_row(5, "Total time used")

        months, incomes, expenses = get_stats()
        months_value.config(text=str(months))
        incomes_value.config(text=str(incomes))
        expenses_value.config(text=str(expenses))

        def update_times():
            if not info_win.winfo_exists():
                return
            session_seconds = time.time() - start_time
            session_value.config(text=format_duration(session_seconds))
            total_value.config(text=format_duration(load_total_time() + session_seconds))
            info_win.after(1000, update_times)

        update_times()

        # HELP TAB
        help_tab = tb.Frame(notebook, padding=(30, 20))
        notebook.add(help_tab, text="Help")
        help_path = resource_path("help.txt")
        if os.path.exists(help_path):
            with open(help_path, "r", encoding="utf-8") as f:
                lines = [line.strip("• ").strip() for line in f if line.strip()]
        else:
            lines = ["help.txt not found"]
        for line in lines:
            tb.Label(help_tab, text=f"• {line}", font=(UI_FONT, 11), justify="left", wraplength=420).pack(
                anchor="w", pady=4)

        # center over the main window, then show and color the title bar (needs a mapped window)
        info_win.update_idletasks()
        width, height = info_win.winfo_reqwidth(), info_win.winfo_reqheight()
        x = main_window.winfo_rootx() + (main_window.winfo_width() - width) // 2
        y = main_window.winfo_rooty() + (main_window.winfo_height() - height) // 3
        info_win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        info_win.deiconify()
        color_title_bar(info_win)
        info_win.focus_force()

    def on_close():
        persist_settings()
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

        list_frame = tb.Frame(canvas)

        #bind canvas width to list_frame width
        def resize_list_frame(event):
            canvas.itemconfig(window_id, width=event.width)

        window_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.bind("<Configure>", resize_list_frame)

        def update_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        list_frame.bind("<Configure>", update_scroll)

        scroll_canvases.append(canvas)
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        return list_frame

    # mouse wheel scrolls the list under the cursor (labels inside the list too)
    scroll_canvases = []

    def on_mousewheel(event):
        mark_activity()
        try:
            widget = main_window.winfo_containing(event.x_root, event.y_root)
        except KeyError:
            # e.g. combobox dropdown, not a tkinter widget
            return
        while widget is not None and widget not in scroll_canvases:
            widget = widget.master
        if widget is None:
            return
        # don't scroll if everything already fits
        bbox = widget.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= widget.winfo_height():
            return
        widget.yview_scroll(int(-event.delta / 120), "units")

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
    # hidden until the welcome screen covers it, otherwise the main UI flashes on start
    main_window.withdraw()
    main_window.iconbitmap(resource_path("app.ico"))
    outline_buttons = []  # filled below, styled by apply_custom_styles
    apply_custom_styles()

    if last_theme == DARKTHEME:
        theme_symbol = LIGHTSYMBOL
    else:
        theme_symbol = DARKSYMBOL

    # TOP BAR: theme left, title centered, actions right
    # side columns share width (uniform) so the title stays truly centered
    top_bar = tb.Frame(main_window)
    top_bar.pack(fill="x", padx=45, pady=(26, 18))
    top_bar.columnconfigure(0, weight=1, uniform="topbar_side")
    top_bar.columnconfigure(2, weight=1, uniform="topbar_side")

    theme_button = tb.Button(top_bar, text=theme_symbol, bootstyle="secondary-outline", padding=(10, 3),
                             width=2, command=lambda: change_theme())
    theme_button.grid(row=0, column=0, sticky="w")

    # padx keeps a gap to the buttons, also raises the window minsize so they never crowd
    tb.Label(top_bar, text="Expense tracker", font=(UI_FONT, 22, "bold")).grid(row=0, column=1, padx=28)

    actions = tb.Frame(top_bar)
    actions.grid(row=0, column=2, sticky="e")
    lock_button = tb.Button(actions, text="Lock", bootstyle="secondary-outline", padding=(10, 3),
                            command=lambda: lock_app())
    lock_button.pack(side="left", padx=(0, 6))
    info_button = tb.Button(actions, text="ⓘ", bootstyle="secondary-outline", padding=(10, 3), width=2,
                            command=lambda: open_info_window())
    info_button.pack(side="left")

    #month/year selection menu: ‹ Month [..] | Year [..] ›
    top_selection_bar = tb.Frame(main_window)
    top_selection_bar.pack(fill="x", pady=0)

    top_selection_bar.columnconfigure(0, weight=1)
    top_selection_bar.columnconfigure(8, weight=1)

    prev_button = tb.Button(top_selection_bar, text="‹", bootstyle="secondary-outline", padding=(10, 2),
                            command=lambda: shift_month(-1))
    prev_button.grid(row=0, column=1, padx=(0, 10))

    #MONTH LABEL
    month_label = tb.Label(top_selection_bar, text="Month:")
    month_label.grid(row=0, column=2, sticky="e", padx=2, pady=0)

    #MONTH COMBO
    month_var = tk.StringVar(value=last_month if last_month in MONTHS else MONTHS[datetime.now().month - 1])

    month_box = tb.Combobox(top_selection_bar, textvariable=month_var, values=MONTHS, width=12, state="readonly")
    month_box.grid(row=0, column=3, sticky="w", padx=4, pady=0)

    #SEPARATOR vertical
    separatorvert = tb.Separator(top_selection_bar, orient=VERTICAL)
    separatorvert.grid(row=0, column=4, sticky="ns", padx=6, pady=0)

    #YEAR LABEL
    year_label = tb.Label(top_selection_bar, text="Year:")
    year_label.grid(row=0, column=5, sticky="e", padx=2, pady=0)

    #YEAR COMBO, years that have data + this year ±1
    year_var = tk.StringVar(value=last_year if last_year and last_year.isdigit() else str(datetime.now().year))

    year_box = tb.Combobox(top_selection_bar, textvariable=year_var, values=year_values(), width=8, state="readonly")
    year_box.grid(row=0, column=6, sticky="w", padx=4, pady=0)

    next_button = tb.Button(top_selection_bar, text="›", bootstyle="secondary-outline", padding=(10, 2),
                            command=lambda: shift_month(1))
    next_button.grid(row=0, column=7, padx=(10, 0))

    month_var.trace_add("write", refresh_lists)
    year_var.trace_add("write", refresh_lists)


    #MAIN CONTENT FRAME
    main_frame = tb.Frame(main_window)
    main_frame.pack(fill="both", expand=True, padx=40, pady=(16, 25))

    #inner CONTENT FRAME
    content_frame = tb.Frame(main_frame)
    content_frame.pack(fill="both", expand=True)

    #THREE SECTIONS
    income_frame = tb.Frame(content_frame, padding=5)

    expense_frame = tb.Frame(content_frame, padding=5)
    total_frame = tb.Frame(content_frame, padding=(0, 5))

    income_frame.pack(fill="both", expand=True, pady=10)
    expense_frame.pack(fill="both", expand=True, pady=10)

    separator1 = tb.Separator(content_frame, orient=HORIZONTAL)
    separator1.pack(fill=X, pady=5)

    total_frame.pack(fill="x", pady=10)

    # income
    tb.Label(income_frame, text="Income (+)", font=(UI_FONT, 14, "bold"), bootstyle="success").pack(anchor="w", pady=(0, 4))

    income_inner = tb.Frame(income_frame)
    income_inner.pack(fill="both", expand=True)

    # incom frame list
    income_list_frame = tb.Frame(income_inner, borderwidth=5, relief="sunken")
    income_list_frame.pack(fill="both", expand=True, side="top", pady=0)

    income_list = make_scrollable_list(income_list_frame, "success-round")

    # incom entry frame
    income_entry_frame = tb.Frame(income_inner)
    income_entry_frame.pack(fill="x", side="bottom")

    income_entry = tb.Entry(income_entry_frame, justify="left", font=(UI_FONT, 10))
    income_entry.pack(fill="x", pady=(10, 0))
    setup_placeholder(income_entry, "add income, note(optional)")
    income_entry.bind("<Return>", lambda e: add_entry("income", income_entry))

    # EXPENSE SECTION
    tb.Label(expense_frame, text="Expense (-)", font=(UI_FONT, 14, "bold"), bootstyle="danger").pack(anchor="w", pady=(0, 4))

    expense_inner = tb.Frame(expense_frame)
    expense_inner.pack(fill="both", expand=True)

    expense_list_frame = tb.Frame(expense_inner, borderwidth=5, relief="sunken")
    expense_list_frame.pack(fill="both", expand=True, side="top")

    expense_list = make_scrollable_list(expense_list_frame, "danger-round")

    expense_entry_frame = tb.Frame(expense_inner)
    expense_entry_frame.pack(fill="x", side="bottom")

    expense_entry = tb.Entry(expense_entry_frame, justify="left", font=(UI_FONT, 10))
    expense_entry.pack(fill="x", pady=(10, 0))
    setup_placeholder(expense_entry, "add expense, note(optional)")
    expense_entry.bind("<Return>", lambda e: add_entry("expense", expense_entry))

    # TOTAL SECTION
    amounts_hidden = tk.BooleanVar(value=last_amounts_hidden)
    hide_lists = tk.BooleanVar(value=last_hide_lists)

    # header row: title + hide/show amounts (+ whether lists are hidden too)
    summary_header = tb.Frame(total_frame)
    summary_header.pack(fill="x", padx=5, pady=(0, 8))
    tb.Label(summary_header, text="Summary", font=(UI_FONT, 14, "bold")).pack(side="left")
    hide_button = tb.Button(summary_header, text="Show amounts" if amounts_hidden.get() else "Hide amounts",
                            bootstyle="secondary-outline", padding=(8, 2), command=toggle_amounts)
    hide_button.pack(side="right")
    hide_lists_toggle = tb.Checkbutton(summary_header, text="Hide in lists too", variable=hide_lists,
                                       bootstyle="round-toggle", command=on_hide_lists_changed)
    hide_lists_toggle.pack(side="right", padx=(0, 14))

    # four stat cards side by side
    cards = tb.Frame(total_frame)
    cards.pack(fill="x")

    def make_card(column, caption, value_bootstyle):
        card = tb.Frame(cards, padding=(12, 8), relief="solid", borderwidth=1)
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        cards.columnconfigure(column, weight=1, uniform="cards")
        tb.Label(card, text=caption, font=(UI_FONT, 9), style="Muted.TLabel").pack(anchor="w")
        value = tb.Label(card, text="–", font=(UI_FONT, 16, "bold"), bootstyle=value_bootstyle)
        value.pack(anchor="w")
        return value

    all_income = make_card(0, "Income", "success")
    all_expense = make_card(1, "Expenses", "danger")
    total_amount = make_card(2, "Remaining", "success")
    amount_of_budget_used = make_card(3, "Budget used", "default")

    budget_bar = StripedProgressBar(total_frame, height=14)
    budget_bar.pack(fill="x", padx=5, pady=(12, 0))

    outline_buttons.extend([theme_button, lock_button, info_button, prev_button, next_button, hide_button])
    apply_custom_styles()

    main_window.protocol("WM_DELETE_WINDOW", on_close)

    # Esc locks, any input counts as activity for the auto lock
    main_window.bind("<Escape>", lock_app)
    for sequence in ("<Motion>", "<KeyPress>", "<ButtonPress>"):
        main_window.bind_all(sequence, mark_activity, add="+")

    # MAINLOOP
    # first load while hidden so the window opens at its final size (no jump behind the welcome screen)
    refresh_lists()
    set_dynamic_minsize(main_window)
    show_welcome()
    main_window.deiconify()
    color_title_bar(main_window)
    check_idle()

    main_window.mainloop()

if __name__ == "__main__":
    run_app()
