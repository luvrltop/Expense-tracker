r"""Build expense_tracker.exe: checks -> tests -> PyInstaller.
The Inno Setup installer is built separately by hand, not from here.

Run in the project folder with the venv active, so the exe gets the venv's packages and custom themes:
    .venv\Scripts\activate
    python build_expense.py              # tests + exe
    python build_expense.py --skip-tests # exe only (not for releases)
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
REQUIRED_THEMES = ("expensetrackerlight", "expensetrackerdark")

def resource(name):
    # absolute, because PyInstaller resolves relative paths from --specpath
    return os.path.join(ROOT, name)


PYINSTALLER_ARGS = [
    resource("expense_tracker.py"),
    "--name", "expense_tracker",                # the installer script expects dist/expense_tracker.exe
    "--onefile",
    "--windowed",
    "--icon", resource("installer.ico"),        # multi-size icon, app.ico is a single 1536x1024 frame
    "--hidden-import", "ttkbootstrap",
    "--hidden-import", "ttkbootstrap.constants",
    "--add-data", resource("app.ico") + ";.",   # window icon + About logo
    "--add-data", resource("help.txt") + ";.",  # About -> Help tab
    "--specpath", resource("build"),            # don't overwrite the hand-made expense_tracker.spec
    "--noconfirm",                              # overwrite dist/ without asking
    "--clean",                                  # no stale cache from earlier builds
]


def step(title):
    print(f"\n=== {title} ===", flush=True)


def fail(message):
    print(f"\nBUILD FAILED: {message}", flush=True)
    sys.exit(1)


def check_environment():
    step("Checking environment")
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        fail("activate the venv first (.venv\\Scripts\\activate), then run: python build_expense.py\n"
             "(global python is missing packages, e.g. requests, and the exe would break)")

    try:
        import PyInstaller
    except ImportError:
        fail("PyInstaller is not installed in the venv: .venv/Scripts/python -m pip install -r requirements.txt")

    # themes come from the venv's ttkbootstrap/themes/user.py (kept outside this repo on purpose)
    try:
        from ttkbootstrap.themes.user import USER_THEMES
    except ImportError:
        USER_THEMES = {}
    missing = [name for name in REQUIRED_THEMES if name not in USER_THEMES]
    if missing:
        fail(f"themes missing from ttkbootstrap/themes/user.py: {', '.join(missing)}\n"
             "copy the newest export from C:\\coding\\ttkcreator_userthemes over user.py")

    from config import VERSION
    print(f"python      {sys.executable}")
    print(f"pyinstaller {PyInstaller.__version__}")
    print(f"version     {VERSION}")
    return VERSION


def run_tests():
    step("Running tests")
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
                            cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if result.returncode != 0:
        fail("tests failed, exe not built")


def build_exe():
    step("Building exe with PyInstaller")
    started = time.time()
    result = subprocess.run([sys.executable, "-m", "PyInstaller", *PYINSTALLER_ARGS], cwd=ROOT)
    if result.returncode != 0:
        fail("PyInstaller failed")
    exe = os.path.join(ROOT, "dist", "expense_tracker.exe")
    size_mb = os.path.getsize(exe) / 1024 / 1024
    print(f"\n{exe} ({size_mb:.1f} MB, {time.time() - started:.0f} s)")


def main():
    parser = argparse.ArgumentParser(description="Build Expense Tracker")
    parser.add_argument("--skip-tests", action="store_true", help="don't run tests first")
    args = parser.parse_args()

    os.chdir(ROOT)
    sys.path.insert(0, ROOT)
    version = check_environment()
    if args.skip_tests:
        step("Tests skipped")
    else:
        run_tests()
    build_exe()
    step(f"Done, version {version}")


if __name__ == "__main__":
    main()
