import pyautogui
import psutil
from pywinauto import Desktop
from pynput import keyboard
import tkinter as tk
import time
from threading import Thread
import pystray
from PIL import Image
import sys
import os

try:
    GAME_PROCESS_NAME = "Palworld-Win64-Shipping.exe"
    COLOR_TOLERANCE = 20
    SWAP_DELAY = 0.1
    REF_WIDTH = 1920
    REF_HEIGHT = 1080
    REF_PIXEL_X = 1573
    REF_PIXEL_Y = 995
    REL_X = REF_PIXEL_X / REF_WIDTH
    REL_Y = REF_PIXEL_Y / REF_HEIGHT
    OVERLAY_REF_X = 1408
    OVERLAY_REF_Y = 956
    OVERLAY_REF_WIDTH = 126
    OVERLAY_REF_HEIGHT = 65
    OVERLAY_REL_X = OVERLAY_REF_X / 1920
    OVERLAY_REL_Y = OVERLAY_REF_Y / 1080
    OVERLAY_REL_WIDTH = OVERLAY_REF_WIDTH / 1920
    OVERLAY_REL_HEIGHT = OVERLAY_REF_HEIGHT / 1080

    SPHERES = [
        ("Pal Sphere", "1–9",  "#21BAF7"),
        ("Mega Sphere", "10–19", "#5DD176"),
        ("Giga Sphere", "20–29", "#FFC74A"),
        ("Hyper Sphere", "30–39", "#F74D52"),
        ("Ultra Sphere", "40–49", "#FF6DAD"),
        ("Legendary Sphere", "50", "#C659EF"),
        ("Ultimate Sphere", "50", "#E769FF"),
        ("Exotic Sphere", "50", "#C5ACEA"),
    ]

    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def color_matches(c1, c2, tolerance):
        return all(abs(a - b) <= tolerance for a, b in zip(c1, c2))

    SPHERES_RGB = [
        (name, lvl, hex_to_rgb(color))
        for name, lvl, color in SPHERES
    ]

    cached_window = None
    last_window_scan = 0
    WINDOW_SCAN_INTERVAL = 5

    def get_palworld_window():
        global cached_window, last_window_scan
        now = time.time()
        if cached_window and now - last_window_scan < WINDOW_SCAN_INTERVAL:
            return cached_window
        windows = Desktop(backend="win32").windows()
        for w in windows:
            try:
                pid = w.process_id()
                if pid and psutil.Process(pid).name() == GAME_PROCESS_NAME:
                    cached_window = w
                    last_window_scan = now
                    return w
            except Exception:
                continue
        cached_window = None
        last_window_scan = now
        return None

    def get_scaled_pixel():
        window = get_palworld_window()
        if not window:
            return None
        rect = window.rectangle()
        x = int(rect.left + rect.width() * REL_X)
        y = int(rect.top + rect.height() * REL_Y)
        return x, y

    def get_overlay_geometry():
        window = get_palworld_window()
        if not window:
            return 100, 100, 126, 65
        rect = window.rectangle()
        x = int(rect.left + rect.width() * OVERLAY_REL_X)
        y = int(rect.top + rect.height() * OVERLAY_REL_Y)
        width = int(rect.width() * OVERLAY_REL_WIDTH)
        height = int(rect.height() * OVERLAY_REL_HEIGHT)
        return x, y, width, height

    def scan_sphere():
        pos = get_scaled_pixel()
        if not pos:
            return None
        try:
            pixel_color = pyautogui.pixel(*pos)
        except Exception:
            return None
        for name, lvl, sphere_color in SPHERES_RGB:
            if color_matches(pixel_color, sphere_color, COLOR_TOLERANCE):
                return lvl
        return None
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "white")
    root.configure(bg="white")

    canvas = tk.Canvas(root, width=126, height=65, bg="white", highlightthickness=0)
    canvas.pack()
    rect = canvas.create_rectangle(0, 0, 126, 65, fill="#333333", outline="#FFD700", width=2)
    text = canvas.create_text(63, 32, text="", fill="yellow", font=("Arial", 24, "bold"))

    def show_overlay(lvl):
        canvas.itemconfig(text, text=lvl)
        canvas.itemconfig(rect, state="normal")
        canvas.itemconfig(text, state="normal")

    def hide_overlay():
        canvas.itemconfig(text, text="")
        canvas.itemconfig(rect, state="hidden")
        canvas.itemconfig(text, state="hidden")

    hide_overlay()

    def update_overlay_position():
        x, y, width, height = get_overlay_geometry()
        root.geometry(f"{width}x{height}+{x}+{y}")
        canvas.config(width=width, height=height)
        canvas.coords(rect, 0, 0, width, height)
        canvas.coords(text, width//2, height//2)
        root.after(100, update_overlay_position)

    update_overlay_position()
    from pynput import keyboard

    CLEAR_KEYS_SPECIAL = {keyboard.Key.esc, keyboard.Key.tab}
    CLEAR_KEYS_NORMAL = {"4", "t", "p", "f", "m"}
    SCAN_KEYS = {"2", "q"}
    q_held = False

    def on_press(key):
        global q_held
        try:
            if key in CLEAR_KEYS_SPECIAL:
                hide_overlay()
                return
            if hasattr(key, "char"):
                k = key.char.lower()
                if k in SCAN_KEYS:
                    if k == "q":
                        if q_held:
                            return
                        q_held = True
                    time.sleep(SWAP_DELAY)
                    lvl = scan_sphere()
                    if lvl:
                        show_overlay(lvl)
                    else:
                        hide_overlay()
                elif k in CLEAR_KEYS_NORMAL:
                    hide_overlay()
        except AttributeError:
            pass

    def on_release(key):
        global q_held
        try:
            if hasattr(key, "char") and key.char.lower() == "q":
                q_held = False
        except AttributeError:
            pass

    listener_thread = Thread(target=lambda: keyboard.Listener(on_press=on_press, on_release=on_release).run(), daemon=True)
    listener_thread.start()
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(base_path, "icon.ico")
    tray_icon_image = Image.open(icon_path)

    def quit_app(icon, item):
        icon.stop()
        root.destroy()

    def tray_menu():
        window_status = "Palworld Found" if get_palworld_window() else "Palworld Missing"
        return pystray.Menu(
            pystray.MenuItem(window_status, lambda: None, enabled=False),
            pystray.MenuItem("Exit Overlay", quit_app)
        )

    def setup_tray():
        icon = pystray.Icon("PalSphereOverlay", tray_icon_image, "PalSphereOverlay", menu=tray_menu())
        icon.run()

    tray_thread = Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    root.mainloop()

except Exception as e:
    print(f"\n[ERROR] {e}")
    input("Press Enter to close...")