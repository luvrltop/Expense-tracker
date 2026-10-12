import sys
import os
import ctypes

def resource_path(relative_path):
    """function for getting resource path"""
    try:
        base_path = sys._MEIPASS  # PyInstaller
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# DwmSetWindowAttribute ids
DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # windows 10 2004+ and 11
DWMWA_CAPTION_COLOR = 35            # windows 11 only
DWMWA_TEXT_COLOR = 36               # windows 11 only

def _colorref(hex_color):
    """#rrggbb -> COLORREF (0x00bbggrr)"""
    h = hex_color.lstrip("#")
    if len(h) == 3:  # short form like #fff
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r

def set_title_bar_colors(window, bg, fg, dark):
    """color the windows title bar to match the theme. silently does nothing where unsupported"""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        # the title bar belongs to the wrapper window, the parent of tk's own hwnd
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dwm = ctypes.windll.dwmapi

        def set_attribute(attribute, value):
            value = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))

        set_attribute(DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))
        set_attribute(DWMWA_CAPTION_COLOR, _colorref(bg))
        set_attribute(DWMWA_TEXT_COLOR, _colorref(fg))
    except Exception:
        pass
