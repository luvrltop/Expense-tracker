# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Keep this file up to date.** Whenever a change in a session affects anything described here, update this file in the same session. This covers new files or modules, changed data formats such as the CSV and settings columns, new UI conventions or patterns, new dependencies, and changed commands. The user relies on this file to continue work across sessions. Do this without being asked, and mention it in the summary to the user.

## Overview

A single-window Windows desktop budget tracker (Tkinter + ttkbootstrap, Python 3.14 in `.venv`). The user enters incomes and expenses per month/year; the app shows totals, remaining budget and the percentage of income spent. It is distributed as a one-file PyInstaller `.exe` through GitHub Releases (`luvrltop/Expense-tracker`).

## Commands

There are no tests or linter config.

Install dependencies:
```bash
.venv/Scripts/python -m pip install -r requirements.txt
```

Run the app:
```bash
.venv/Scripts/python expense_tracker.py
```

Build the exe (output goes to `dist/`):
```bash
pyinstaller expense_tracker.spec
```
The equivalent full command line is in the comment on line 1 of `expense_tracker.py`. `*.spec` is gitignored, so the spec file exists only locally.

## Architecture

- `expense_tracker.py`: all UI and behavior live inside one `run_app()` function as nested closures. These closures share the widgets (`month_var`, `year_var`, `income_list`, etc.) through the enclosing scope, so a closure may refer to a widget that is created further down. Two functions drive the data flow:
  - `refresh_lists()` reloads the selected month's CSV, rebuilds both lists with `add_list_row()` and then calls `update_summary()`. It is wired to `trace_add` on the month and year vars and runs after every add, edit, delete or undo. Do not draw rows anywhere else. To change month and year together, use `set_view()`. It suppresses the two trace refreshes (`view["batch"]`) and refreshes once.
  - `update_summary()` recomputes the four summary cards and the progress bar from the CSV.
- `storage.py`: one CSV per month, named `{year}_{month}.csv`, for example `2026_October.csv`. Each row is `income|expense, "<amount>€ <note>"`. Totals are recomputed on each refresh by parsing the first whitespace token of every entry (`parse_euro`), so there is no other state to keep in sync. Entries are normalized to `"<num>€ <note>"` before saving (`normalize_euro` in `expense_tracker.py`), so the amount must stay the first token.
- `split_entry(text)` gives `(amount | None, note)`. Rows and totals use it. Input is validated with `parse_input()`: an entry without a parseable amount is not saved, and the field flashes red (`flash_invalid`). The stored text format is unchanged; only the display is formatted.
- `delete_item` / `insert_item` / `update_item(kind, index, ...)` in `storage.py` work by position among rows of that kind, which is the same order as `load_items`. They do not match by text, so duplicate entries are handled correctly. `delete_item` returns the deleted text. `insert_item` puts it back at the same position for undo.
- `get_years_with_data()` scans the CSV file names. The year combobox shows those years plus the current year ±1.
- `settings.py`: `settings.csv` holds a single row `month, year, theme, amounts_hidden(0/1), hide_lists(0/1)`. Older 3- and 4-column files are still accepted, and missing flags default to False. `load_settings()` returns 5 values. Save through `persist_settings()` in `expense_tracker.py`, which collects every field. `total_time.txt` holds the cumulative usage time in seconds. Settings are written in `on_close`, and also immediately when the hide toggles change.
- Start screen `show_welcome()` is a privacy feature. It is a full-window `tb.Frame` placed over the whole UI (`place(relwidth=1, relheight=1)` + `lift()`), so amounts aren't visible when the app opens in public. It shows a greeting, a live clock, the date and the month/year being opened, plus a loading section: a status text, a percentage and a `StripedProgressBar`. The loading is a list of `steps` (text, percent, action) run by `loading_tick()`. The action does the real work, and the bar eases toward the step's percent so each step stays readable. The update check (`get_latest_version`) runs in a daemon thread so the UI doesn't freeze. The popup is shown on the main thread when loading finishes, via `check_for_updates(..., latest=...)`. Continue stays disabled until 100%, then Continue or Enter destroys the overlay. Startup order matters to avoid flashing the money UI: `withdraw()` right after `tb.Window`, then build the UI, then `refresh_lists()` + `set_dynamic_minsize()` while hidden so the window opens at its final size, then `show_welcome()`, then `deiconify()`. Its `<Return>` binding is on the main window and is removed on close, so the Enter handlers of the entry fields keep working. This replaced the old minimized start (`iconify()`) and the welcome messagebox.
- The same screen is the **lock screen**: `show_welcome(locked=True)`, which skips the loading section and enables Continue immediately. It is triggered by `lock_app()` from the Lock button, from Esc (bound on the main window), or from `check_idle()` after `AUTO_LOCK_MINUTES` without input. Activity is tracked with `bind_all(..., add="+")` on Motion, KeyPress and ButtonPress, and in `on_mousewheel`. `welcome_state["shown"]` prevents stacking two overlays. Widgets that handle Esc themselves (the inline edit entry) must return `"break"`, otherwise Esc also locks the app.
- Row actions:
  - ✕ deletes immediately and shows an undo toast (`show_toast`, `TOAST_MS`). The toast is a `place()`d frame at the bottom, and only one is shown at a time.
  - A double click turns the row into an inline `tb.Entry` (`start_edit`). Enter saves, and Esc or focus-out cancels.
- Privacy toggles: "Hide amounts" (`amounts_hidden`) masks the summary cards. "Hide in lists too" (`hide_lists`) also masks the row amounts. Rows check `lists_masked()`.
- `widgets.py`: custom canvas widgets. `StripedProgressBar` is the budget bar with sliding stripes, because ttkbootstrap's `striped` style can't animate. Its colors are passed in from the theme on every `update_summary()`.
- `config.py`: `VERSION` is the single source of the version string. On import, the module creates the data directory.
- `update_checker.py`:
  - `get_latest_release(current)` reads **all** GitHub releases (`/releases`, not `/releases/latest`, which hides pre-releases) and returns the newest one as `{"version", "url"}`.
    - It returns `None` if the check failed, and `{"version": None, ...}` if there are no releases.
    - Pre-releases (alpha/beta/rc) are offered **only when the running `VERSION` is itself a pre-release**. Normal users skip them whether GitHub flags them or only the tag says so.
  - `extract_version` keeps the pre-release suffix (`v1.4.0-beta1` → `1.4.0-beta1`), so `packaging` orders it correctly: beta1 < beta2 < final.
  - `is_newer(release, current)` checks whether that release is newer than the running version.
  - `check_for_updates(..., release=...)` shows the popup. The popup and the About link open that release's own page (`url`).
- Release convention:
  - Tag `vX.Y.Z` for releases and `vX.Y.Z-beta1` / `-alpha1` / `-rc1` for test builds, and mark the latter as **Pre-release** on GitHub.
  - Set `config.VERSION` to the same string without the `v`, e.g. `"1.4.0-beta1"`.
- All user data goes to `%APPDATA%\Expense-Tracker\` (`config.BASE_DIR`), never to the repo.
- Bundled resources (`app.ico`, `help.txt`) must be loaded through `resource_path()` so they resolve inside the PyInstaller `_MEIPASS` bundle. New resource files also need to be added to the `datas`/`--add-data` list. `help_functions.py` has the shared copy of `resource_path`, and `run_app()` currently redefines it locally.
- `lang.py` is an empty placeholder for future localization.

## Themes

`expensetrackerlight` and `expensetrackerdark` are custom ttkbootstrap themes. They are intentionally **not** stored in this repo; do not add them here. They live in `.venv/Lib/site-packages/ttkbootstrap/themes/user.py`, written by ttkcreator. The user keeps the exports in their own repo (`C:\coding\ttkcreator_userthemes`, github.com/luvrltop/ttkcreator_userthemes) as dated `user<DDMMYYYY>.py` files. After recreating the venv or upgrading ttkbootstrap, copy the newest export over `user.py`. Otherwise `tb.Window(themename=...)` fails at startup.

### UI conventions

- Prefer ttkbootstrap widgets (`tb.*`) over plain `tk.*`. Use plain tk only when ttk can't do the job, such as `tk.Canvas` for the scrollable lists and the progress bar.
- Never hardcode colors. Use `bootstyle=` (`success`/`danger`/`secondary`...) or read `main_window.style.colors` (`bg`, `fg`, `active`, `danger`, ...). `Colors.update_hsv()` derives lighter or darker shades.
- ttk styles are per theme. Anything configured with `style.configure(...)` must be reapplied after `theme_use()`. `change_theme()` does this by calling `apply_custom_styles()` (row, empty-state, placeholder and toast styles) and `update_summary()`. Add new custom styles to that path.
- List rows use the `Row.*` / `RowHover.*` / `Row(Hover)Delete.TLabel` styles. The hover highlight swaps between these styles on `<Enter>`/`<Leave>`. `<Leave>` also fires when the pointer moves onto a child widget, so it checks with `winfo_containing`.
- Mouse-wheel scrolling uses one `bind_all` handler (`on_mousewheel`). It walks up from the widget under the pointer to a canvas registered in `scroll_canvases`.
- Font for new UI is `UI_FONT` ("Segoe UI").
- Money is always displayed with `format_money()` in Finnish format (`1 500,00 €`, with no-break spaces). Never show the raw stored text. Summary cards use `format_euro()` and rows use `display_amount()`; both respect the hide toggles (`****`). Row amounts sit in a fixed-width (`AMOUNT_WIDTH`) right-aligned column.
- Don't use the theme's `secondary` color for text. It is too faint, especially in the dark theme (#555555). Use `style="Muted.TLabel"` for captions and hint text. Its color is `mix_colors(bg, fg, 0.6)`, and the placeholder and empty-state styles use the same value.
- Entry fields use `setup_placeholder()` for grey hint text (`Placeholder.TEntry`). Read them with `entry_value()`, which returns "" while the placeholder is shown.
- Top bar layout:
  - Theme toggle on the left (fixed `width=2`), the title centered, and Lock + Info on the right.
  - It is a 3-column grid, and the side columns share `uniform="topbar_side"` so the title stays exactly centered.
  - All outline buttons (theme, Lock, ⓘ, ‹ ›, Hide amounts) use the custom style `OUTLINE_BUTTON_STYLE` ("App.secondary.Outline.TButton"), because the theme's `secondary` color was too faint to see.
    - Text is `fg`, the border is `mix_colors(bg, fg, 0.45)`, and the hover background is `active`.
    - Create such buttons with `bootstyle="secondary-outline"`, so that the parent style exists, and add them to `outline_buttons`.
    - `apply_custom_styles()` reassigns the style on every theme change, because ttkbootstrap resets bootstyle widgets then.
  - Don't add U+FE0E variation selectors to symbols, because Tk draws them as extra width.
  - The theme toggle and the ⓘ info button are icon-only buttons with `width=2`.
- Windows title bar colors: `set_title_bar_colors()` in `help_functions.py` uses `DwmSetWindowAttribute`.
  - It sets immersive dark mode (attribute 20), plus caption and text color (attributes 35 and 36, Windows 11 only). It fails silently elsewhere.
  - `color_title_bar(window)` in `expense_tracker.py` passes the theme's `bg`/`fg`.
  - It only works on a mapped window, because `GetParent` returns 0 before that. So build new toplevels with the pattern `withdraw()` → build → `deiconify()` → `color_title_bar()`.
  - Call it for every new toplevel window, and give each one `iconbitmap(resource_path("app.ico"))`. It is rerun on theme change for the main window and for an open About window.
- About window: `open_info_window()` opens a single instance and focuses it if it is already open. Its layout is modeled on the user's todolist app and has three tabs:
  - **Info**: logo, name, version, an update check in a thread that is polled on the main thread, a GitHub link and ©.
  - **Statistics**: `storage.get_stats()` plus session and total time.
  - **Help**: the lines of `help.txt`.
  - The logo is `app.ico` loaded with PIL (`load_logo`), because it is already bundled and no extra data files are needed. The ico frame is 3:2, not square, so it is loaded with `thumbnail()` to keep the aspect ratio.

### Testing UI changes

There is no test suite. To verify a change, run `run_app()` from a throwaway script with these patches:
- Point `storage.BASE_DIR` and `settings.SETTINGS_FILE`/`TIME_FILE` at a temp dir before importing `expense_tracker`, so the user's real data in `%APPDATA%` is never touched.
- Stub `et.get_latest_release` (used by the loading screen and the About window). Return e.g. `{"version": "1.3.1", "url": "..."}`, or `None` for a failed check.
- Replace `tk.Misc.mainloop` with a function that drives the window (`event_generate`, `.invoke()`), takes screenshots with `PIL.ImageGrab` and destroys the window.
- The welcome overlay covers everything at start. Wait until the Continue button's state is `normal` (loading takes about 1.5 s), then dismiss it with `w.event_generate("<Return>")` before testing the main UI.
- `event_generate("<Double-Button-1>")` is not allowed. Simulate a double click with two `<ButtonPress-1>`/`<ButtonRelease-1>` pairs at the same x/y.
- To test auto lock, set `et.AUTO_LOCK_MINUTES` small. `check_idle` runs every 10 s.

Set `PYTHONIOENCODING=utf-8` when printing `€`/`✕`.
