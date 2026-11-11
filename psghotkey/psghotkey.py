import PySimpleGUI as sg
import keyboard
import ctypes
import socket, struct, subprocess, threading, time
import tkinter as tk
import os, shlex, sys, tempfile
import base64, io, math, traceback
from collections import deque
from typing import List, Any, Dict, ClassVar
from PIL import Image, ImageDraw, ImageFont




r"""

      _____  _______  ______ _     _  _____  _______ _     _ _______ __   __
     |_____] |______ |  ____ |_____| |     |    |    |____/  |______   \_/  
     |       ______| |_____| |     | |_____|    |    |    \_ |______    |
     
     
    psghotkey

    A simple hotkey manager that runs in the system tray.

    Packages required:
        PySimpleGUI
        keyboard
        psgtray
        Pillow

    Define your hotkeys in the Hotkeys window (the gear on the card, or right-click > Hotkeys...).  They are stored in your own
    psghotkey.json user settings file, so every user has their own set.  At the moment, the actions are to insert text or launch a program.
    Nothing is defined until you add it.  Some examples of the kind of thing you can set up:
        ctrl+alt+p      Insert text      PySimpleGUI
        ctrl+alt+e      Insert text      your.name@example.com
        ctrl+alt+t      Insert text      Thanks for your help!
        ctrl+alt+n      Launch program   notepad.exe
        ctrl+alt+c      Launch program   calc.exe
    Hotkey names are the keyboard package's:  modifiers + key joined with "+", e.g.  ctrl+alt+h   alt+f9   ctrl+shift+1
    The card (the main window):  one row per hotkey, with a green dot when it works and a red one when Windows refused it (a bad key name, or
    another program already has it - point at the row to see).  A hotkey's row lights up as it fires and RECENT lists the last few.  Click a row
    to edit it.  Right-click for the menu:  Hotkeys..., Minimize to tray when closed, Start with Windows, in the tray, Theme (the widgets' 32),
    Brightness..., Edit Me, Version, Exit - laid out like every PySimpleGUI tray app, with psghotkey and its version at the top.
    The tray icon:  click = show / hide the card,  right-click = the same menu.  Closing the card (its x or Esc) minimizes it to the tray
    (right-click > Minimize to tray when closed turns that off).  You can add your own items to the menu in make_menu() and handle them in the event loop.
    Right-click > Start with Windows, in the tray: a shortcut in your Startup folder starts psghotkey with Windows, quietly in the tray
    (pythonw psghotkey.py --tray), so your hotkeys work after every restart.  Off until you tick it.
    psghotkey --demo shows example hotkeys, for a screenshot - it registers nothing, leaves your settings alone and doesn't stop a running psghotkey.

    On Windows each hotkey is registered with Windows itself (RegisterHotKey), so Windows does the matching, the key combination is
    swallowed instead of reaching the program underneath, and there is no keyboard hook for Windows to silently drop after a sleep,
    lock or busy moment (the keyboard package's hook has that problem).  The keyboard package is used to type the text and to record
    a hotkey with the Rec button.  On other systems the hotkeys go through keyboard.add_hotkey().

    Copyright 2021-2026 PySimpleGUI
    Licensed as LGPL3.
"""



VERSION = '6.1.2'
__version__ = VERSION
APP_NAME = 'psghotkey'                  # the name the program shows - spelled like the package, the psghotkey command and psghotkey.json

"""
Changelog since last major release

6.0     12-Apr-2026     Bumped ver from 5 to 6 to move to LGPL3
                        License changed to LGPL3    
                        Removed the docstring example code and added commented out launch example
6.0.1   12-Apr-2026     Fixed screenshot in ReadMe for PyPI release
6.0.2   12-Apr-2026     One more try to fix screenshot.  Needed to add a hardcoded URL to image on GitHub for PyPI to work
6.0.2   27-Oct-2026     Claude: Single instance - launching psghotkey while a copy is already running tells the old copy to exit
                        (cleanly, through its event loop so the tray icon is removed) and the new copy takes over. Uses a
                        localhost socket on INSTANCE_PORT; claim_single_instance() + instance_listener() do the work.
6.0.3   27-Oct-2026     Claude: Hotkeys moved out of the code and into the user settings file (psghotkey.json) so everyone has their own.
                        New "Settings" tray menu item / window button opens a built-in hotkey editor (add, delete, reorder, record a
                        hotkey from the keyboard, insert-text or launch-program actions) - same design as the MiniLauncher setup window.
                        Hotkeys are reloaded when the Settings window closes. First run writes the original alt+shift+p -> "PySimpleGUI"
                        hotkey as a starting point.
6.0.3   27-Oct-2026     Claude: Settings window redesign - toolbar across the top grouped by job (Add/Delete | Up/Down | All/None | Save/Reload/
                        Clear all), colour-coded buttons (green Save turns gold when there are unsaved changes, red for destructive), status
                        bar showing count / checked / saved state and the settings filename, prompt to save on close, Ctrl+S saves.
6.0.3   27-Oct-2026     Claude: Keyboard handling now uses keyboard.add_hotkey() per hotkey (register_hotkeys) instead of a low-level hook that
                        was called on every key press. Main window redesigned - "N hotkeys active" header, table of the hotkeys (double-click
                        opens Settings), timestamped log that shows each hotkey as it fires and highlights its row, toolbar with Settings /
                        Hide to tray / Edit Me / Versions / Exit, Escape hides to tray. First run now writes 5 example hotkeys. Docstring
                        cleaned up (pingmote references removed).
6.0.3   27-Oct-2026     Claude: Fixed startup crash "'_KeyboardListener' object has no attribute 'blocking_hotkeys'" - keyboard.unhook_all_hotkeys()
                        fails before the keyboard listener has started, so hotkeys are now removed one by one with the handles that
                        keyboard.add_hotkey() returned (unregister_hotkeys). Docstring made a raw string to silence the ASCII-art backslash SyntaxWarning.
6.0.3   27-Oct-2026     Claude: Settings window now has standard dialog buttons - OK (save + close, Enter/Ctrl+S), Apply (save, stay open, hotkeys
                        re-registered immediately so they can be tried), Cancel (Escape; asks before discarding unsaved changes). Reload and the
                        separate Close button removed. Hotkeys stay live while Settings is open; paused only while Rec is recording.
6.0.3   27-Oct-2026     Claude: Example hotkey for PySimpleGUI is ctrl+alt+p (was alt+shift+p) - defaults, docstring, placeholder.
6.0.3   27-Oct-2026     Claude: No hotkeys are written on first run any more - a new install starts with an empty list and the log says to open
                        Settings. The examples stay in the docstring as suggestions only.
6.0.3   27-Oct-2026     Claude: Cancel / Clear all prompts could appear BEHIND the keep-on-top settings window (Cancel looked dead when there were
                        unsaved changes). confirm() drops keep-on-top while the question is up and places it over the window.
6.0.3   27-Oct-2026     Claude: Fixed Cancel button doing nothing - it shared the key K_CANCEL with the titlebar X, and PySimpleGUI renames a
                        duplicate key, so the button's event never matched. The X is back on its own key ('Exit', handled the same way).
6.0.3   29-Oct-2026     Claude: Hotkeys stopped firing after a while - Windows silently removes the keyboard package's low-level hook when its
                        callback stalls past the hook timeout (sleep, lock, busy). Hotkeys are now registered with Windows (RegisterHotKey,
                        ctypes, class WindowsHotkeys): no hook to lose, and the combo no longer leaks to the app underneath. A hotkey another
                        program already owns is reported in the log. Rec button now gives up after 15 s instead of hanging.
6.0.3   29-Oct-2026     Claude: Inserted text was ignored by console / tkinter programs - it was typed while Ctrl/Alt were still held (the
                        keyboard package's hook used to release them; there's no hook now). type_text() waits for the modifiers to be let go.
6.0.3   29-Oct-2026     Claude: New tray / window icon - a keycap with the PySimpleGUI icon printed on it (64x64). The cap fills the whole
                        square - a tray cell is only 16 px, so any margin in the art makes the icon look tiny next to its neighbours.
6.0.3   29-Oct-2026     Claude: Starts hidden in the tray - the main window only appears when asked for (double-click the tray icon or
                        right-click -> Show Window). Startup balloon says so.
6.0.3   30-Oct-2026     Claude: Settings window - removed the Up/Down reorder buttons and arrow-key moves; the order of the hotkeys has no effect
                        on anything, so there was nothing to reorder for.
6.0.3   30-Oct-2026     Claude: Launching a second copy left it without hotkeys - the old copy released the single-instance port before its
                        hotkeys (held until the exit popup closed), so RegisterHotKey failed in the new one. The exiting copy now unregisters
                        its hotkeys as soon as it leaves the event loop; a copy that just replaced a running one retries for up to ~6 s.
6.1     31-Oct-2026     Bumped version to 6.1 since this is the first set of Claude changes in psghotkey                        
6.1     03-Nov-2026     Claude: Tray works like psgsnip's (tray_app_recipe.md): a single click shows / hides the window, right-click opens the
                        menu in the window's colors (no more Windows-gray menu), new "Minimize to tray when closed" toggle.  Removed the
                        Change Icon test menu (Happy / Sad / Plain) and the Show / Hide Window items, and the balloon on every hide.
6.1.1   03-Nov-2026     Claude: New look - the widgets' card (psgsnip, Pip Refresh, PSG Dock).  The main window is one rounded card drawn with
                        Pillow, no Windows title bar: a row per hotkey (green dot = working, red = Windows refused it), the row lights up as
                        the hotkey fires, RECENT lists the last 5.  Click a row or the gear to edit, the x or Esc minimize to the tray.
                        Pillow is now required.  The card remembers where it was left.
6.1.1   03-Nov-2026     Claude: Themes - right-click > Theme (the widgets' 32, with color chips) and Brightness...  The Hotkeys window, the
                        right-click menus and the popups follow the theme.
6.1.1   03-Nov-2026     Claude: The Settings window is now the Hotkeys window (it edits the list - that isn't settings), in PSG Dock's Programs
                        window look: title strip with an x that turns red, dragged by the strip, themed entries that stretch with the window,
                        a blank entry to fill in when there are none, status bar with a size grip.
6.1.1   03-Nov-2026     Claude: The program calls itself psghotkey everywhere it shows its name (PySimpleHotkey was a very old name).
6.1.1   03-Nov-2026     Claude: FIX: saving the hotkeys wiped the program's own settings (Minimize to tray...) - they share psghotkey.json.
                        Only the hotkey entries are rewritten now.
6.1.1   03-Nov-2026     Claude: A program that can't be launched shows in RECENT in red (it was only printed, and a .pyw has no console).
                        main() shows a crash with popup_error_with_traceback.  Right-click > Versions is Version.
6.1.1   04-Nov-2026     Claude: --demo shows example hotkeys and a made-up RECENT list, for screenshots: it registers nothing, keeps its settings in
                        the temp folder (your psghotkey.json isn't touched), has no tray icon, and a running psghotkey keeps running.
6.1.2   11-Nov-2026     Claude: Right-click > Start with Windows, in the tray - a shortcut in your Startup folder starts psghotkey with Windows,
                        quietly in the tray (pythonw psghotkey.py --tray: no balloon).  Off until you tick it.  The right-click menu is laid out
                        like every PySimpleGUI tray app: psghotkey 6.1.2 at the top (click it for the Version window), Version 6.1.2 at the bottom.
"""




# The hotkeys come from the user settings file (psghotkey.json).  Edit them in the Hotkeys window (the card's gear, or right-click > Hotkeys...)
hotkey_dict = {}        # maps a hotkey string (e.g. 'ctrl+alt+p') to the callable that performs its action
hotkey_info = {}        # maps a hotkey string to its (action, value) - what the card's rows show

SETTINGS_FILENAME = 'psghotkey.json'    # the hotkeys AND the program's own settings (theme, tray, where the card is) - save_hotkey_list() keeps the latter
ACTION_TEXT = 'Insert text'
ACTION_LAUNCH = 'Launch program'
DEMO = '--demo' in sys.argv              # psghotkey --demo: example hotkeys for a screenshot - nothing of yours is read, changed or stopped
DEMO_HOTKEYS = [('ctrl+alt+p', ACTION_TEXT, 'PySimpleGUI'), ('ctrl+alt+t', ACTION_TEXT, 'Thanks for your help!'), ('ctrl+alt+n', ACTION_LAUNCH, 'notepad.exe'),
                ('ctrl+alt+c', ACTION_LAUNCH, 'calc.exe')]
DEMO_FOLDER = os.path.join(tempfile.gettempdir(), 'psghotkey_demo')     # the demo's own psghotkey.json (its theme and place are kept there)
ACTIONS = (ACTION_TEXT, ACTION_LAUNCH)
ACTION_SHORT = {ACTION_TEXT: 'Type', ACTION_LAUNCH: 'Run'}       # the card's ACTION column
PYTHON_NAMES = ('python', 'python.exe', 'pythonw', 'pythonw.exe', 'python3', 'py', 'py.exe', 'pyw', 'pyw.exe')     # 'pythonw x.pyw' shows as x.pyw

# The card (the main window) - keys
K_IMAGE = '-IMAGE-'
K_HOVER = '-HOVER-'                  # the mouse moved onto another part of the card  (value: the part, or None)
K_CLICK = '-CLICK-'                  # a part of the card was clicked  (value: the part)
K_MOVED = '-MOVED-'                  # the card was dragged to a new place - remember it
K_SCROLL = '-SCROLL-'                # mouse wheel over the card  (value: +1 = down, -1 = up)
K_FLASH_OFF = '-FLASH OFF-'          # timer: a fired hotkey's row stops glowing
K_HOTKEY_FIRED = '-HOTKEY FIRED-'    # event sent (from the hotkey thread) when a hotkey runs, value = (the hotkey, None or what went wrong)
K_HOTKEYS = '-HOTKEYS-'              # right-click > Hotkeys...  (the Hotkeys window)
K_THEME = '-THEME-'                  # settings-file entry, and the prefix of the Theme menu keys
KT_THEME = lambda name: f'{K_THEME}{name}'
K_LOCATION = '-LOCATION-'            # settings-file entry: where the card was left
K_ESCAPE = '-ESCAPE-'                # Esc on the card: minimize to the tray (or end the program when tray mode is off)

# The card - look
TRANSPARENT = '#010203'              # window color key: anything this color is see-through and click-through (the rounded corners)
SEE_THROUGH = sg.running_windows()   # only Windows has the color key - elsewhere the card has square corners
# --- WIDGET THEMES: the same block in every card widget (master copy in modern_widget_recipe.md) - change it in all of them at once ---
# card = background, border = outline, track = gauge track / lines, text = main text, dim = labels.   16 dark first, then 16 light: the Theme menu
# shows them as two columns of color chips.  ForestFloor and CrimsonVelvet come from Mike's dark themes; the other colored darks follow their lead.
THEMES = {'Toybox':        {'card': '#141821', 'border': '#2f3a4e', 'track': '#1e2430', 'text': '#e6eaf2', 'dim': '#8a93a3'},
          'Carbon':        {'card': '#121212', 'border': '#2e2e2e', 'track': '#1f1f1f', 'text': '#e0e0e0', 'dim': '#8c8c8c'},
          'Slate':         {'card': '#2a3140', 'border': '#48526a', 'track': '#363e50', 'text': '#eef1f6', 'dim': '#a3acbd'},
          'CrimsonVelvet': {'card': '#5e0d1f', 'border': '#8f1530', 'track': '#781429', 'text': '#f9d276', 'dim': '#d6a7a0'},
          'Ember':         {'card': '#451f11', 'border': '#773c27', 'track': '#5c2f1e', 'text': '#f1e4df', 'dim': '#bd9f93'},
          'Espresso':      {'card': '#2c2016', 'border': '#594331', 'track': '#423224', 'text': '#f1e7df', 'dim': '#bda693'},
          'Bronze':        {'card': '#48310f', 'border': '#7b5823', 'track': '#60441b', 'text': '#f1eadf', 'dim': '#bdac93'},
          'Olive':         {'card': '#2a3013', 'border': '#545f2b', 'track': '#3e4620', 'text': '#eef1df', 'dim': '#b5bd93'},
          'ForestFloor':   {'card': '#101c0e', 'border': '#2a4424', 'track': '#1b2e18', 'text': '#d0e0c8', 'dim': '#83977d'},
          'Jade':          {'card': '#113124', 'border': '#29614a', 'track': '#1e4836', 'text': '#dff1ea', 'dim': '#93bdac'},
          'Lagoon':        {'card': '#0e3434', 'border': '#236767', 'track': '#1a4c4c', 'text': '#dff1f1', 'dim': '#93bdbd'},
          'Petrol':        {'card': '#0f303e', 'border': '#235a71', 'track': '#1b4456', 'text': '#dfecf1', 'dim': '#93b1bd'},
          'Cobalt':        {'card': '#132949', 'border': '#294a7a', 'track': '#20395f', 'text': '#dfe6f1', 'dim': '#93a4bd'},
          'Indigo':        {'card': '#1e1e48', 'border': '#383876', 'track': '#2c2c5d', 'text': '#dfdff1', 'dim': '#9393bd'},
          'Plum':          {'card': '#341c3f', 'border': '#5a376c', 'track': '#472b54', 'text': '#ebdff1', 'dim': '#af93bd'},
          'Mulberry':      {'card': '#3f1731', 'border': '#6e3057', 'track': '#552544', 'text': '#f1dfea', 'dim': '#bd93ae'},
          'Paper':         {'card': '#f5f7fb', 'border': '#c9d1dc', 'track': '#dadfe8', 'text': '#1b2130', 'dim': '#5c6676'},
          'Fog':           {'card': '#dde2e8', 'border': '#b8c0ca', 'track': '#c5ccd5', 'text': '#1b2028', 'dim': '#545d69'},
          'Stone':         {'card': '#e1dedb', 'border': '#b9b5b1', 'track': '#c5c2be', 'text': '#2b2117', 'dim': '#63574b'},
          'Sand':          {'card': '#e7dfcf', 'border': '#c1b6a4', 'track': '#cbc2b3', 'text': '#2b2417', 'dim': '#675942'},
          'Linen':         {'card': '#f7f2e8', 'border': '#dcd1bd', 'track': '#e4dac9', 'text': '#2b2620', 'dim': '#73685a'},
          'Butter':        {'card': '#fbf5dc', 'border': '#e3d7a6', 'track': '#e8ddb1', 'text': '#2e2a18', 'dim': '#766c4c'},
          'Peach':         {'card': '#fce9df', 'border': '#dfbdaa', 'track': '#e6ccbc', 'text': '#2b1e17', 'dim': '#705d51'},
          'Blush':         {'card': '#faedf0', 'border': '#eccad2', 'track': '#efd1d8', 'text': '#321c22', 'dim': '#80606a'},
          'Rose':          {'card': '#ecd5dd', 'border': '#c7a9b3', 'track': '#d1b8c0', 'text': '#2b171e', 'dim': '#70515c'},
          'Orchid':        {'card': '#f4e5f5', 'border': '#d1b6d3', 'track': '#dbc6dc', 'text': '#2a172b', 'dim': '#6e5170'},
          'Lavender':      {'card': '#f0ecfa', 'border': '#d2c9ec', 'track': '#dad3f0', 'text': '#231e33', 'dim': '#665e80'},
          'Periwinkle':    {'card': '#e3e6f7', 'border': '#b2b7d6', 'track': '#c3c7df', 'text': '#171a2b', 'dim': '#515670'},
          'Sky':           {'card': '#e7f0fa', 'border': '#bdd2ea', 'track': '#c7daee', 'text': '#18222f', 'dim': '#53667d'},
          'Aqua':          {'card': '#ddf2f3', 'border': '#aecfd0', 'track': '#bfd9d9', 'text': '#172a2b', 'dim': '#516f70'},
          'Mint':          {'card': '#e8f5ee', 'border': '#bcdccb', 'track': '#c5e1d2', 'text': '#1b2a22', 'dim': '#557064'},
          'Pistachio':     {'card': '#ebf3dd', 'border': '#c4cfaf', 'track': '#cfd9bf', 'text': '#242b17', 'dim': '#657051'}}
OLD_THEME_NAMES = {'Midnight': 'Carbon', 'VoidBlue': 'Carbon', 'DarkSlate': 'Slate', 'MidnightPurple': 'Plum', 'DeepOceanTeal': 'Lagoon'}   # saved by older versions
# --- end WIDGET THEMES ---
C_ACCENT = '#1e9bff'                 # a fired hotkey's row, a checked entry in the Hotkeys window
C_GOOD, C_WARN, C_BAD = '#2ecc71', '#e8a33d', '#ff6b6b'      # working / some not working / refused - darker on a light card (status_color)
C_CLOSE = '#c0392b'                  # the x becomes red under the mouse
C_MENU_SEL = '#2a62a8'               # menu highlight (white text) and the buttons - the same blue in every tray app
C_SWATCH_EDGE = '#7c8594'            # outline of the color chips in the Theme menu - mid gray shows on dark and light menus
FONT_MENU = ('Segoe UI', 10)
FONT_UI = 'Segoe UI'                 # the Hotkeys window and the popups
FONT_NAMES = {True: ('segoeuib.ttf', 'DejaVuSans-Bold.ttf'), False: ('segoeui.ttf', 'DejaVuSans.ttf')}     # the card's bold / regular: Windows first, then Linux
COLOR_SAVE = 'white on #2e7d32'      # Hotkeys window buttons - green = save, gold = unsaved changes, red = destructive
COLOR_SAVE_DIRTY = 'black on #ffc107'
COLOR_DANGER = 'white on #b71c1c'

# card geometry in design pixels (96 dpi); everything is multiplied by the scale when drawn
CARD_W, RADIUS = 480, 18
HEAD_H, COLS_H, ROW_H, FOOT_H = 42, 22, 28, 32         # title strip, column headings, one hotkey, bottom line
ROW_TOP = HEAD_H + COLS_H + 2
GEAR_X, CLOSE_X, BTN_Y, BTN_R = CARD_W - 47, CARD_W - 20, 21, 11
COL_KEY, COL_ACTION, COL_VALUE = 34, 188, 262          # x of the HOTKEY, ACTION and TEXT OR PROGRAM columns
MAX_ROWS = 12                        # hotkeys the card shows at once - the mouse wheel scrolls through more
RECENT_N, RECENT_H = 5, 20           # RECENT: how many firings it lists, and its line height
FLASH_MS = 1500                      # how long a fired hotkey's row glows


def launch_program(path):
    """ Launch a program.  .py/.pyw files are run with the Python interpreter, anything else is run as a command line """
    path = path.strip().strip('"')
    if path.lower().endswith(('.py', '.pyw')):
        sg.execute_py_file(path, cwd=os.path.dirname(path) or None)
    else:
        cmd = [c.strip('"') for c in shlex.split(path, posix=False)]
        sg.execute_command_subprocess(cmd[0], *cmd[1:])


def type_text(text):
    """ Type text into whatever has the focus.  On Windows, first wait (up to 2 s) for the hotkey's modifier keys to be released - characters
        typed while Ctrl/Alt are held are ignored by most programs.  (The keyboard package used to release them from what its hook saw.) """
    if sys.platform != 'win32':
        keyboard.write(text)
        return
    import ctypes
    user32 = ctypes.windll.user32
    user32.GetAsyncKeyState.restype = ctypes.c_short
    VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN = 0x10, 0x11, 0x12, 0x5B, 0x5C
    deadline = time.time() + 2.0
    while time.time() < deadline and any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN)):
        time.sleep(0.01)
    keyboard.write(text, restore_state_after=False)


def make_action(hotkey, action, value):
    """ Returns the callable the hotkey thread runs when the hotkey is pressed.  It does the action, then tells the card - and what went wrong, if anything """
    def run():
        error = None
        try:
            if action == ACTION_LAUNCH:
                launch_program(value)
            else:
                type_text(value)
        except Exception as e:
            error = str(e) or type(e).__name__
        if G.main_window is not None:
            G.main_window.write_event_value(K_HOTKEY_FIRED, (hotkey, error))
    return run


def build_hotkey_dict():
    """ (Re)build hotkey_dict and hotkey_info from the settings file """
    hotkey_dict.clear()
    hotkey_info.clear()
    for hotkey, action, value in load_hotkey_list():
        hotkey_dict[hotkey] = make_action(hotkey, action, value)
        hotkey_info[hotkey] = (action, value)


class WindowsHotkeys:
    """ Global hotkeys through the Windows RegisterHotKey API.  No keyboard hook, so there is nothing for Windows to silently remove when the
        machine sleeps, locks or is busy - the problem the keyboard package's hook has.  Windows posts WM_HOTKEY to the thread that registered
        the hotkey, so one background thread registers them and runs a message loop; set_hotkeys() hands it a new set through a queue. """
    WM_HOTKEY = 0x0312
    WM_APP_UPDATE = 0x8001
    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
    MODIFIERS = {'ctrl': MOD_CONTROL, 'control': MOD_CONTROL, 'alt': MOD_ALT, 'menu': MOD_ALT, 'alt gr': MOD_ALT, 'shift': MOD_SHIFT, 'win': MOD_WIN, 'windows': MOD_WIN, 'cmd': MOD_WIN, 'super': MOD_WIN}
    VK_NAMES = {'space': 0x20, 'enter': 0x0D, 'return': 0x0D, 'tab': 0x09, 'esc': 0x1B, 'escape': 0x1B, 'backspace': 0x08, 'delete': 0x2E, 'del': 0x2E, 'insert': 0x2D, 'ins': 0x2D,
                'home': 0x24, 'end': 0x23, 'page up': 0x21, 'pageup': 0x21, 'pgup': 0x21, 'page down': 0x22, 'pagedown': 0x22, 'pgdn': 0x22, 'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
                'print screen': 0x2C, 'pause': 0x13, 'caps lock': 0x14, 'num lock': 0x90, 'scroll lock': 0x91, 'apps': 0x5D, 'browser back': 0xA6, 'browser forward': 0xA7,
                'volume mute': 0xAD, 'volume down': 0xAE, 'volume up': 0xAF, 'next track': 0xB0, 'previous track': 0xB1, 'play/pause media': 0xB3, 'play/pause': 0xB3,
                'plus': 0xBB, 'minus': 0xBD, 'comma': 0xBC, 'period': 0xBE, 'decimal': 0x6E, 'separator': 0x6C, 'multiply': 0x6A, 'add': 0x6B, 'subtract': 0x6D, 'divide': 0x6F}

    def __init__(self):
        import queue
        self.requests, self.results = queue.Queue(), queue.Queue()
        self.actions = {}                               # hotkey id -> callable
        self.thread_id = None
        self.ready = threading.Event()
        threading.Thread(target=self._message_loop, daemon=True).start()
        self.ready.wait(5)

    @classmethod
    def parse(cls, hotkey):
        """ 'ctrl+alt+p' -> (modifier flags, virtual key code) or None if a key name isn't understood """
        import ctypes
        mods, vk = 0, None
        for part in [p.strip().lower() for p in hotkey.replace('++', '+plus').split('+')]:      # 'ctrl++' means the + key
            if part == '':
                continue
            name = part[5:] if part.startswith('left ') else part[6:] if part.startswith('right ') else part
            if name in cls.MODIFIERS:
                mods |= cls.MODIFIERS[name]
                continue
            if vk is not None:
                return None                             # two non-modifier keys
            if name in cls.VK_NAMES:
                vk = cls.VK_NAMES[name]
            elif len(name) == 1 and name.isalnum() and name.isascii():
                vk = ord(name.upper())
            elif len(name) > 1 and name[0] == 'f' and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
                vk = 0x70 + int(name[1:]) - 1
            elif len(name) == 1:
                code = ctypes.windll.user32.VkKeyScanW(ord(name))
                if code == -1:
                    return None
                vk = code & 0xFF
            else:
                return None
        return (mods, vk) if vk is not None else None

    def set_hotkeys(self, hotkeys):
        """ Replace the registered set with `hotkeys` {name: callable}.  Returns the names Windows refused (bad key name, or in use by another program). """
        import ctypes
        if self.thread_id is None:
            return list(hotkeys)
        self.requests.put(dict(hotkeys))
        ctypes.windll.user32.PostThreadMessageW(self.thread_id, self.WM_APP_UPDATE, 0, 0)
        try:
            return self.results.get(timeout=5)
        except Exception:
            return list(hotkeys)

    def _message_loop(self):
        import ctypes
        from ctypes import wintypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0x0400, 0x0400, 0)      # forces Windows to create this thread's message queue
        self.thread_id = kernel32.GetCurrentThreadId()
        self.ready.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == self.WM_HOTKEY:
                action = self.actions.get(msg.wParam)
                if action is not None:
                    try:
                        action()
                    except Exception as e:
                        print(f'Hotkey action failed: {e}')
            elif msg.message == self.WM_APP_UPDATE:
                hotkeys = self.requests.get()
                for hotkey_id in list(self.actions):
                    user32.UnregisterHotKey(None, hotkey_id)
                self.actions.clear()
                bad = []
                for hotkey_id, (hotkey, func) in enumerate(hotkeys.items(), 1):
                    parsed = self.parse(hotkey)
                    if parsed is None or not user32.RegisterHotKey(None, hotkey_id, parsed[0] | self.MOD_NOREPEAT, parsed[1]):
                        bad.append(hotkey)
                    else:
                        self.actions[hotkey_id] = func
                self.results.put(bad)


hotkey_handles = []     # non-Windows only: what keyboard.add_hotkey() returned for each registered hotkey - each one is the function that removes that hotkey


def unregister_hotkeys():
    """ Remove every hotkey we registered """
    if sys.platform == 'win32':
        if G.win_hotkeys is not None:
            G.win_hotkeys.set_hotkeys({})
        return
    for remove in hotkey_handles:                       # (keyboard.unhook_all_hotkeys() crashes if the keyboard listener hasn't started yet, so we don't use it)
        try:
            remove()
        except (KeyError, ValueError):
            pass
    hotkey_handles.clear()


def register_hotkeys():
    """ Register every hotkey in hotkey_dict - with Windows (RegisterHotKey) on Windows, with the keyboard package elsewhere.
        Returns the list of hotkeys that were refused (bad key names, or already taken by another program). """
    if DEMO:
        return []                                       # the demo registers nothing: a running psghotkey keeps its hotkeys
    if sys.platform == 'win32':
        if G.win_hotkeys is None:
            G.win_hotkeys = WindowsHotkeys()
        return G.win_hotkeys.set_hotkeys(hotkey_dict)
    unregister_hotkeys()
    bad = []
    for hotkey, func in hotkey_dict.items():
        try:
            hotkey_handles.append(keyboard.add_hotkey(hotkey, func))
        except (ValueError, KeyError):
            bad.append(hotkey)
    return bad


def refresh_main_window(window:sg.Window):
    """ Register the hotkeys and show them on the card - with a red dot on any that Windows refused """
    G.bad = set(register_hotkeys())
    G.top = max(0, min(G.top, len(hotkey_info) - MAX_ROWS))
    refused = len(G.bad)
    set_status(f'{refused} hotkey{"s" * (refused != 1)} not working - point at the red dot to see why' if refused else '', 'bad')
    redraw(window)


#  ██╗  ██╗ ██████╗ ████████╗██╗  ██╗███████╗██╗   ██╗███████╗    ██╗    ██╗██╗███╗   ██╗██████╗  ██████╗ ██╗    ██╗
#  ██║  ██║██╔═══██╗╚══██╔══╝██║ ██╔╝██╔════╝╚██╗ ██╔╝██╔════╝    ██║    ██║██║████╗  ██║██╔══██╗██╔═══██╗██║    ██║
#  ███████║██║   ██║   ██║   █████╔╝ █████╗   ╚████╔╝ ███████╗    ██║ █╗ ██║██║██╔██╗ ██║██║  ██║██║   ██║██║ █╗ ██║
#  ██╔══██║██║   ██║   ██║   ██╔═██╗ ██╔══╝    ╚██╔╝  ╚════██║    ██║███╗██║██║██║╚██╗██║██║  ██║██║   ██║██║███╗██║
#  ██║  ██║╚██████╔╝   ██║   ██║  ██╗███████╗   ██║   ███████║    ╚███╔███╔╝██║██║ ╚████║██████╔╝╚██████╔╝╚███╔███╔╝
#  ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝     ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝  ╚══╝╚══╝
#
#   A scrollable list of entries, one per hotkey, with + Add / - Delete / Clear all, All / None and OK / Apply / Cancel.
#   (Same design as PSG Dock's Programs window, in the card's theme.)  An entry has 3 things:
#       Hotkey      e.g. ctrl+alt+p   (type it, or click Rec and press the key combination)
#       Action      Insert text  or  Launch program
#       Value       the text to type, or the path / command line to launch
#   Keyboard shortcuts:  PgUp/PgDn = scroll a page     Home/End = top/bottom     Enter / Ctrl+S = OK     Escape = Cancel

LIST_HEIGHT = 520                    # the list's height in design pixels (less on a short screen)
HOTKEY_INPUT_LENGTH = 28
VALUE_INPUT_LENGTH = 80
K_STRIP = '-STRIP-'                  # the title strip - the window is dragged by it
MENU_EDITME_VER_EXIT = ['', ['    Edit Me::Edit Me', f'    Version {VERSION}::Version', '    Exit::Exit']]


class Block:
    active_blocks: ClassVar[Dict[int, "Block"]] = {}
    def __init__(self, block_num, hotkey, action, value):
        self.block_num = block_num
        self.hotkey = hotkey
        self.action = action
        self.value = value


class G:
    block_number = 0                                    # Counter for adding blocks
    hotkey_settings : sg.UserSettings = None
    dirty = False                                       # True while the Hotkeys window has unsaved changes
    main_window : sg.Window = None                      # so hotkey callbacks (hotkey thread) can send events to the card
    win_hotkeys : 'WindowsHotkeys' = None               # the RegisterHotKey thread (Windows only), created on first use
    window : sg.Window = None                           # the card (the same window as main_window)
    scale = 1.0                                         # screen dpi / 96
    theme = 'Toybox'
    bright = 0                                          # the Brightness level (BRIGHTNESS block)
    tuned = {}                                          # (theme, level) -> its colors at that level
    swatches = {}                                       # (theme, level) -> its chip in the Theme menu
    fonts = {}                                          # (bold, px) -> a Pillow font
    images = {}                                         # pictures resized for the display scaling
    hits = []                                           # [(x0, y0, x1, y1, part)] in design pixels, filled by render()
    hover = None                                        # the part of the card under the mouse
    press = None                                        # (x_root, y_root, part) where the left button went down on the card
    height = 0                                          # the card's height in design pixels when it was last drawn
    top = 0                                             # the first hotkey row shown (the wheel scrolls when there are more than MAX_ROWS)
    bad = set()                                         # the hotkeys Windows refused
    flash = {}                                          # hotkey -> when it fired - its row glows for FLASH_MS
    recent = deque(maxlen=RECENT_N)                     # (time, hotkey, what it did, None or what went wrong), newest first
    status = ('', None)                                 # (text, kind) for the card's bottom line - kind None, 'good' or 'bad'


# Saved in the settings file (one set per hotkey, numbered)
K_HOTKEY = '-HOTKEY-'
KT_HOTKEY = lambda num: (K_HOTKEY, num)
K_ACTION = '-ACTION-'
KT_ACTION = lambda num: (K_ACTION, num)
K_VALUE = '-VALUE-'
KT_VALUE = lambda num: (K_VALUE, num)

# Hotkeys window only
K_BLOCK = '-BLOCK-'
KT_BLOCK = lambda num: (K_BLOCK, num)
K_COLUMN = '-COLUMN-'
KT_COLUMN = lambda num: (K_COLUMN, num)
K_CBOX = '-CBOX-'
KT_CBOX = lambda num: (K_CBOX, num)
K_DEL = '-DELETE-'
KT_DEL = lambda num: (K_DEL, num)
K_RECORD = '-RECORD-'                           # Rec button - capture a hotkey from the keyboard
KT_RECORD = lambda num: (K_RECORD, num)
K_RECORDED = '-RECORDED-'                       # Event from the recording thread with the captured hotkey
KT_RECORDED = lambda num: (K_RECORDED, num)

K_ALL_COLS = '-ALL COLS-'
K_PAGE_UP = '-PAGE UP-'
K_PAGE_DOWN = '-PAGE DOWN-'
K_HOME = '-HOME-'
K_END = '-END-'
K_OK = '-OK-'
K_APPLY = '-APPLY-'
K_CANCEL = '-CANCEL-'
K_SEL_ALL = '-SELECT ALL-'
K_SEL_NONE = '-SELECT NONE-'
K_STATUS = '-STATUS-'


# ------------------------------------------------------------ Settings file load / save ------------------------------------------------------------

def get_settings() -> sg.UserSettings:
    if G.hotkey_settings is None:
        G.hotkey_settings = sg.UserSettings(SETTINGS_FILENAME, path=DEMO_FOLDER) if DEMO else sg.UserSettings(SETTINGS_FILENAME)
    return G.hotkey_settings


def settings_filename() -> str:
    """ Full path of the settings file """
    return get_settings().get_filename()


def load_hotkey_list() -> List[tuple]:
    """ Read the settings file and return a list of (hotkey, action, value) tuples in saved order.  No file yet = no hotkeys. """
    settings = get_settings()
    saved = settings.load() if settings.exists() else {}
    hotkeys = []
    for key in saved.keys():
        if isinstance(key, tuple) and key[0] == K_HOTKEY:
            num = key[1]
            hotkey = str(saved.get(KT_HOTKEY(num), '')).strip().lower()
            action = saved.get(KT_ACTION(num), ACTION_TEXT)
            value = str(saved.get(KT_VALUE(num), ''))
            if hotkey:
                hotkeys.append((hotkey, action, value))
    return hotkeys


def save_hotkey_list(hotkeys: List[tuple]):
    """ Write a list of (hotkey, action, value) tuples to the settings file, replacing the hotkeys that were there.  The program's own settings
        (theme, brightness, tray, where the card is) are in the same file - they are kept """
    settings = get_settings()
    settings.write_new_dictionary({key: value for key, value in settings.load().items() if not isinstance(key, tuple)})
    for num, (hotkey, action, value) in enumerate(hotkeys):
        settings.set(KT_HOTKEY(num), hotkey)
        settings.set(KT_ACTION(num), action)
        settings.set(KT_VALUE(num), value)


def load_blocks(window:sg.Window):
    del_all_blocks(window)
    try:
        for hotkey, action, value in load_hotkey_list():
            block_num = add_block(window)
            block = Block.active_blocks[block_num]
            block.hotkey, block.action, block.value = hotkey, action, value
            window[KT_HOTKEY(block_num)].update(hotkey)
            window[KT_ACTION(block_num)].update(action)
            window[KT_VALUE(block_num)].update(value)
    except Exception as e:
        sg.popup_error_with_traceback('Error loading saved hotkeys', e)
    window.refresh()
    window[K_ALL_COLS].contents_changed()
    window.refresh()


def save_blocks(window:sg.Window):
    hotkeys = []
    for key in Block.active_blocks.keys():
        if KT_BLOCK(key) in window.key_dict.keys():
            hotkey = window[KT_HOTKEY(key)].get().strip().lower()
            if hotkey:
                hotkeys.append((hotkey, window[KT_ACTION(key)].get(), window[KT_VALUE(key)].get()))
    save_hotkey_list(hotkeys)
    sg.popup_quick_message(f'Saved {len(hotkeys)} hotkey{"s" * (len(hotkeys) != 1)}', font=(FONT_UI, 16), text_color='white', background_color='#2e7d32', keep_on_top=True)


# ------------------------------------------------------------ Blocks (one per hotkey) ------------------------------------------------------------

def make_a_block() -> sg.Frame:
    """ One hotkey in the list:   [ ]  hotkey ..........  Rec   action ......            trash
                                         text to insert  -or-  path / command to launch .......... """
    block_num = G.block_number
    Block.active_blocks[G.block_number] = Block(block_num=G.block_number, hotkey='', action=ACTION_TEXT, value='')
    G.block_number += 1
    T = ui_colors()
    ph = dict(placeholder_text_color=T['faint'], placeholder_background_color=T['input'])

    block_layout = [[sg.Checkbox('', k=KT_CBOX(block_num), enable_events=True, p=((4, 0), 0), tooltip='Check to delete it with  − Delete'),
                     sg.Input(k=KT_HOTKEY(block_num), enable_events=True, placeholder='Hotkey   e.g. ctrl+alt+p', font=(FONT_UI, 12, 'bold'), s=HOTKEY_INPUT_LENGTH, p=(2, (6, 2)),
                              tooltip='Modifiers + key, e.g.  ctrl+alt+h   ctrl+shift+1   alt+f9\nor click Rec and press the keys', **ph),
                     sg.B('Rec', k=KT_RECORD(block_num), button_color=rec_colors(), tooltip='Click, then press the key combination you want', p=(4, (6, 2))),
                     sg.Combo(ACTIONS, default_value=ACTION_TEXT, k=KT_ACTION(block_num), readonly=True, enable_events=True, s=(15, 1), p=(6, (6, 2))),
                     sg.Push(),
                     sg.B(image_source=scaled_png(trash_icon, 25), mouseover_image_source=scaled_png(trash_icon_red, 25), button_color=(T['card'], T['card']),
                          border_width=0, k=KT_DEL(block_num), p=((2, 6), (6, 2)), tooltip='Delete this hotkey')],
                    [sg.Input(k=KT_VALUE(block_num), enable_events=True, placeholder='Text to insert   -or-   path / command to launch', s=VALUE_INPUT_LENGTH,
                              p=((30, 6), (2, 8)), expand_x=True, **ph)]]

    block = sg.Frame('', [[sg.Column(block_layout, k=KT_COLUMN(block_num), expand_x=True, pad=0)]], k=KT_BLOCK(block_num), border_width_no_relief=2,
                     border_color=entry_border(False), expand_x=True, p=(4, 3))
    return block


def add_block(window):
    window.extend_layout(window[K_ALL_COLS], [[make_a_block()]])
    window.refresh()
    window[K_ALL_COLS].contents_changed()
    window.refresh()
    style_menus(window)                                 # the new entry's elements came with right-click menus of their own - Windows gray until styled
    theme_menus(window)
    return G.block_number - 1


def del_block(window, block_num):
    try:
        block_to_delete = int(block_num)
        key_to_delete = KT_BLOCK(block_to_delete)
    except Exception:
        return None
    if key_to_delete in window.key_dict.keys():
        del_an_elem(window, window[key_to_delete])
        window.refresh()
        window[K_ALL_COLS].contents_changed()
    try:
        del Block.active_blocks[block_to_delete]
    except Exception as e:
        sg.popup_error_with_traceback(f'Error deleting block {block_to_delete}', e)
    return key_to_delete


def del_all_blocks(window:sg.Window):
    for key in list(Block.active_blocks.keys()):
        del_block(window, key)


def del_checked_blocks(window:sg.Window):
    for key in list(Block.active_blocks.keys()):
        if window[KT_CBOX(key)].get():
            del_block(window, key)


def update_block_elements(window:sg.Window, block:Block):
    window[KT_HOTKEY(block.block_num)].update(block.hotkey)
    window[KT_ACTION(block.block_num)].update(block.action)
    window[KT_VALUE(block.block_num)].update(block.value)


def record_hotkey_thread(window:sg.Window, block_num):
    """ Thread: wait for the user to press a key combination, then send it to the window as a KT_RECORDED event """
    try:
        hotkey = keyboard.read_hotkey(suppress=False)
    except Exception as e:
        hotkey = None
        print(f'Hotkey recording failed: {e}')
    window.write_event_value(KT_RECORDED(block_num), hotkey)


def record_timeout(window:sg.Window, block_num):
    """ Timer: tell the settings window the recording gave up.  Harmless if the window has closed by then. """
    try:
        window.write_event_value(KT_RECORDED(block_num), None)
    except Exception:
        pass


# ------------------------------------------------------------ Mini window (no titlebar, a title strip) ------------------------------------------------------------

# noinspection PyPep8Naming
def MiniWindow(title: str, layout: List, close_key: Any = 'Exit', **kwargs: Any) -> sg.Window:
    """ Returns a Window with no titlebar, in the theme's colors: a title strip (icon, title, version, an x that sends close_key and turns red under
        the mouse) over the layout, in a thin border.  It moves by dragging the strip, so a click in the layout never moves it.  It starts invisible
        (alpha 0) - place it, then set_alpha(1).  place_window() does both """
    T = ui_colors()
    menu_bg, menu_fg = menu_colors()
    window = sg.Window(f'{APP_NAME} - {title}', wrap_in_border(title, layout, close_key), no_titlebar=True, grab_anywhere=False, keep_on_top=True, finalize=True,
                       margins=(0, 0), alpha_channel=0, icon=window_icon(), right_click_menu_background_color=menu_bg, right_click_menu_text_color=menu_fg,
                       right_click_menu_selected_colors=('#ffffff', C_MENU_SEL), right_click_menu_font=FONT_MENU, **kwargs)
    close = window[close_key].Widget
    close.bind('<Enter>', lambda e: close.configure(bg=C_CLOSE, fg='#ffffff'))
    close.bind('<Leave>', lambda e: close.configure(bg=T['strip'], fg=T['dim']))
    drag_by_strip(window, window[K_STRIP].Widget, skip=close)
    style_menus(window)
    theme_menus(window)
    return window


def wrap_in_border(title: str, layout_rows: list, close_key: Any = 'Exit') -> list:
    """
        ┌────────────────────────────────────────────────┐
        │ [icon] Title   psghotkey v6.1.1            ✕   │   <- the title strip, a shade off the background
        │   ...layout_rows...                            │
        └────────────────────────────────────────────────┘
    """
    T = ui_colors()
    strip = [sg.Image(data=scaled_png(window_icon(), 22), background_color=T['strip'], p=((10, 6), 6)),
             sg.Text(title, font=(FONT_UI, 13, 'bold'), text_color=T['text'], background_color=T['strip'], p=(0, 6)),
             sg.Text(f'{APP_NAME}  v{VERSION}', font=(FONT_UI, 9), text_color=T['dim'], background_color=T['strip'], p=((8, 0), (10, 4))),
             sg.Push(background_color=T['strip']),
             sg.Text('  ✕  ', key=close_key, font=(FONT_UI, 12), text_color=T['dim'], background_color=T['strip'], enable_events=True, p=0, tooltip='Close   (Escape)')]
    body = [[sg.Column([strip], key=K_STRIP, background_color=T['strip'], expand_x=True, p=0)], *layout_rows]
    return [[sg.Frame('', body, border_width_no_relief=1, border_color=T['border'], p=0, expand_x=True, expand_y=True)]]


def drag_by_strip(window, strip, skip=None):
    """ Move a window by dragging its title strip (any of it but skip, the x) """
    start = {}

    def press(e):
        start['p'] = (e.x_root, e.y_root, window.TKroot.winfo_x(), window.TKroot.winfo_y())

    def motion(e):
        p = start.get('p')
        if p:
            window.TKroot.geometry(f'+{p[2] + e.x_root - p[0]}+{p[3] + e.y_root - p[1]}')

    def bind(widget):
        if widget is skip:
            return
        widget.bind('<ButtonPress-1>', press, add='+')
        widget.bind('<B1-Motion>', motion, add='+')
        for child in widget.winfo_children():
            bind(child)

    bind(strip)


def place_window(window, card=None):
    """ Where the Hotkeys window opens: beside the card when it is showing (on the side with more room), else in the middle of the screen the mouse
        is on - all of it on that screen.  Then it is made visible """
    window.refresh()
    w, h = window.TKroot.winfo_width(), window.TKroot.winfo_height()
    if card is not None and not window_hidden(card):
        cx, cy = card.current_location()
        cw, ch = card.size
        left, top, right, bottom = work_area(cx + cw // 2, cy + ch // 2)
        gap = round(10 * G.scale)
        x, y = (cx - w - gap if cx - left > right - cx - cw else cx + cw + gap), cy
    else:
        left, top, right, bottom = work_area(*window.TKroot.winfo_pointerxy())
        x, y = (left + right - w) // 2, (top + bottom - h) // 2
    window.move(max(left, min(x, right - w)), max(top, min(y, bottom - h)))
    window.refresh()                                    # let the move happen first - bring_to_front() before it puts the window back where it opened
    window.set_alpha(1)
    window.bring_to_front()


# ------------------------------------------------------------ Delete an element from a window ------------------------------------------------------------

def del_an_elem(window:sg.Window, elem:sg.Element):
    elem.update(visible=False)
    widget = elem.Widget
    widget.pack_forget()
    widget.destroy()
    if hasattr(widget, 'image'):
        del widget.image
    del widget

    if elem.TKStringVar is not None:
        del elem.TKStringVar
    if elem.TKIntVar is not None:
        del elem.TKIntVar
    if elem.TKText is not None:
        del elem.TKText
    if elem.TKEntry is not None:
        del elem.TKEntry
    if elem.TKImage is not None:
        del elem.TKImage

    rowframe_children = elem.ParentRowFrame.winfo_children()
    if len(rowframe_children) == 0:
        elem.ParentRowFrame.destroy()
        del elem.ParentRowFrame
    remove_elem_from_nested(elem.ParentContainer.Rows, elem)
    del elem.ParentContainer
    del window.AllKeysDict[elem.key]


def remove_elem_from_nested(container, target):
    if isinstance(container, list):
        i = 0
        while i < len(container):
            item = container[i]
            if item is target:
                del container[i]          # remove this slot
                continue                  # don't advance i; next item shifts here
            remove_elem_from_nested(item, target)  # recurse into nested lists/tuples
            i += 1


# ------------------------------------------------------------ The Hotkeys window ------------------------------------------------------------

def entry_border(checked):
    """ An entry's outline: the theme's border color, blue when its box is checked """
    return C_ACCENT if checked else ui_colors()['border']


def rec_colors():
    """ The Rec button: a quiet button in the theme's colors (it turns red while it records) """
    T = ui_colors()
    return T['text'], mix(T['card'], T['text'], 0.14)


def dirty_text_color():
    """ The gold 'UNSAVED CHANGES' text - darker on a light theme, where the bright gold is hard to read """
    return '#9a6f00' if ui_colors()['light'] else '#ffc107'


def check_all_blocks(window:sg.Window, checked):
    for key in Block.active_blocks:
        window[KT_CBOX(key)].update(checked)
        window[KT_BLOCK(key)].update(border_color=entry_border(checked))


def num_checked_blocks(window:sg.Window):
    return sum(1 for key in Block.active_blocks if window[KT_CBOX(key)].get())


def update_status(window:sg.Window):
    """ Refresh the status bar and the Apply button colour (gold = unsaved changes) """
    num = len(Block.active_blocks)
    state = 'UNSAVED CHANGES' if G.dirty else 'saved'
    window[K_STATUS].update(f'{num} hotkey{"s" if num != 1 else ""}   ·   {num_checked_blocks(window)} checked   ·   {state}',
                            text_color=dirty_text_color() if G.dirty else ui_colors()['text'])
    window[K_APPLY].update(button_color=COLOR_SAVE_DIRTY if G.dirty else sg.theme_button_color())


def confirm(window:sg.Window, question, title='Confirm') -> bool:
    """ Yes/No question that is guaranteed to appear ON TOP of the settings window.  The settings window is keep-on-top, so a plain popup
        can come up behind it and look as if the button did nothing.  Drops keep-on-top for the moment and places the popup over the window. """
    window.keep_on_top_clear()
    x, y = window.current_location()
    answer = sg.popup_yes_no(question, title=title, keep_on_top=True, modal=True, location=(x + 120, y + 120))
    window.keep_on_top_set()
    window.bring_to_front()
    return answer == 'Yes'


def apply_settings(window:sg.Window):
    """ Save the list, then make the hotkeys live and refresh the card """
    save_blocks(window)
    G.dirty = False
    build_hotkey_dict()
    if G.main_window is not None:
        refresh_main_window(G.main_window)
    else:
        register_hotkeys()


def focus_entry(window:sg.Window, index):
    """ Scroll the list to the index-th entry and put the cursor in its hotkey box """
    keys = list(Block.active_blocks)
    if not 0 <= index < len(keys):
        return
    num = keys[index]
    window.refresh()
    column = window[K_ALL_COLS].widget
    row = window[KT_BLOCK(num)].Widget.master                                           # the entry's row frame - its y is in the list's own coordinates
    column.canvas.yview_moveto(max(0, row.winfo_y() - 40) / max(1, column.TKFrame.winfo_height()))
    window[KT_HOTKEY(num)].set_focus()
    window[KT_HOTKEY(num)].update(select=True)


def hotkeys_window(focus=None, card=None):
    """ The Hotkeys window - add, change or remove hotkeys.  focus = the index of a hotkey to put the cursor in.  card = the card window, which it
        opens beside.  Returns when the window is closed.  OK and Apply save the list, make it live and refresh the card. """
    T = ui_colors()
    Block.active_blocks = {}
    col_layouts = [[]]
    col_layouts += [[make_a_block()]]       # add a dummy block so that the column width is set correctly

    #  Toolbar - grouped left to right:  list editing | selection ......... OK / Apply / Cancel
    toolbar = [sg.B('+ Add', k='Add', tooltip='Add a new hotkey at the end of the list'),
               sg.B('− Delete', k='Delete', button_color=COLOR_DANGER, tooltip='Delete the checked hotkeys'),
               sg.B('Clear all', k='Clear', button_color=COLOR_DANGER, tooltip='Remove every hotkey from the list   (nothing is written until OK or Apply)'),
               sg.VerticalSeparator(p=(8, 2)),
               sg.B('☑ All', k=K_SEL_ALL, tooltip='Check every hotkey'),
               sg.B('☐ None', k=K_SEL_NONE, tooltip='Uncheck every hotkey'),
               sg.Push(),
               sg.B('OK', k=K_OK, button_color=COLOR_SAVE, s=7, tooltip='Save and close   (Enter, Ctrl+S)'),
               sg.B('Apply', k=K_APPLY, s=7, tooltip='Save and make the hotkeys live, but stay open'),
               sg.B('Cancel', k=K_CANCEL, s=7, tooltip='Close without saving   (Escape)')]
    list_height = min(round(LIST_HEIGHT * G.scale), sg.Window.get_screen_size()[1] - round(260 * G.scale))
    all_columns = sg.Column(col_layouts, size=(None, list_height), k=K_ALL_COLS, vertical_scroll_only=True, scrollable=True, expand_y=True, expand_x=True, p=(6, 2),
                            sbar_trough_color=T['card'], sbar_background_color=T['border'], sbar_arrow_color=T['dim'], sbar_frame_color=T['card'],
                            sbar_relief=sg.RELIEF_FLAT)
    hint = 'Rec: click it, then press the keys.     Insert text types the text for you;  Launch program runs a program or a command.'
    status_bar = [sg.T('', k=K_STATUS, font=(FONT_UI, 10)), sg.Push(),                           # file name only - the full path is in its tooltip, so the bar stays narrow
                  sg.T(os.path.basename(settings_filename()), font=(FONT_UI, 9), text_color=T['faint'], tooltip=f'The hotkeys are saved in\n{settings_filename()}'),
                  sg.Sizegrip()]
    layout = [[sg.Column([toolbar], expand_x=True, p=(8, (8, 2)))],
              [sg.T(hint, font=(FONT_UI, 9), text_color=T['dim'], p=(12, (2, 4)))],
              [all_columns],
              [sg.Column([status_bar], expand_x=True, p=(8, (2, 4)))]]

    # the strip's x sends 'Exit', handled like Cancel
    window = MiniWindow('Hotkeys', layout, close_key='Exit', resizable=True, use_min_size=True, right_click_menu=MENU_EDITME_VER_EXIT)

    del col_layouts
    load_blocks(window)
    if not Block.active_blocks:                         # none yet: one blank entry to fill in (a blank entry isn't saved)
        add_block(window)
        focus = 0
    scroller = window[K_ALL_COLS].widget                # entries stretch to the list's width (the inner frame is a canvas window item)
    scroller.canvas.bind('<Configure>', lambda e: scroller.canvas.itemconfigure(scroller.frame_id, width=e.width), add='+')
    scroller.canvas.itemconfigure(scroller.frame_id, width=scroller.canvas.winfo_width())      # the <Configure> binding came after the first layout

    for key, seq in ((K_PAGE_UP, '<Prior>'), (K_PAGE_DOWN, '<Next>'), (K_HOME, '<Home>'), (K_END, '<End>'), (K_CANCEL, '<Escape>'), (K_OK, '<Return>'), (K_OK, '<Control-s>')):
        window.bind(seq, key)
    scroll_canvas = scroller.canvas
    recording_block = None
    G.dirty = False
    update_status(window)
    place_window(window, card)
    if focus is not None:
        focus_entry(window, focus)

    while True:
        event, values = window.read()
        if isinstance(event, str) and '::' in event:            # right-click menu items come back as 'label::key'
            event = event.split('::')[-1]
        if event == sg.WIN_CLOSED:
            break
        if event in ('Exit', K_CANCEL):
            if not G.dirty or confirm(window, 'Discard your unsaved changes?', 'Unsaved changes'):
                break
            continue
        if event == K_OK:
            apply_settings(window)
            break
        window.refresh()

        if event == 'Version':
            sg.popup_scrolled(__file__, f'{APP_NAME}  version {VERSION}', sg.get_versions(), keep_on_top=True, non_blocking=True, size=(70, 10))
        elif event == 'Edit Me':
            sg.execute_editor(__file__)
        elif event == 'Add':
            add_block(window)
            focus_entry(window, len(Block.active_blocks) - 1)
            G.dirty = True
        elif event == 'Delete':
            if num_checked_blocks(window):
                del_checked_blocks(window)
                G.dirty = True
        elif event == K_APPLY:
            apply_settings(window)
        elif event == 'Clear':
            if Block.active_blocks and confirm(window, 'Remove every hotkey from the list?'):
                del_all_blocks(window)
                G.dirty = True
        elif event in (K_SEL_ALL, K_SEL_NONE):
            check_all_blocks(window, event == K_SEL_ALL)
        elif event == K_PAGE_UP:
            scroll_canvas.yview_scroll(-1, 'pages')
        elif event == K_PAGE_DOWN:
            scroll_canvas.yview_scroll(1, 'pages')
        elif event == K_HOME:
            scroll_canvas.yview_moveto(0)
        elif event == K_END:
            scroll_canvas.yview_moveto(1)
        elif isinstance(event, tuple):              # events from the elements inside a block
            block_num = event[1]
            if block_num not in Block.active_blocks:    # a stale event from a block that's been deleted
                continue
            if event[0] == K_DEL:
                del_block(window, block_num)
                window.refresh()
                window[K_ALL_COLS].contents_changed()
                G.dirty = True
            elif event[0] == K_HOTKEY:
                Block.active_blocks[block_num].hotkey = values[event]
                G.dirty = True
            elif event[0] == K_ACTION:
                Block.active_blocks[block_num].action = values[event]
                G.dirty = True
            elif event[0] == K_VALUE:
                Block.active_blocks[block_num].value = values[event]
                G.dirty = True
            elif event[0] == K_CBOX:
                window[KT_BLOCK(block_num)].update(border_color=entry_border(window[KT_CBOX(block_num)].get()))
            elif event[0] == K_RECORD:
                if recording_block is None:
                    recording_block = block_num
                    unregister_hotkeys()                            # nothing fires while the new one is being recorded
                    window[KT_RECORD(block_num)].update('...', button_color='white on red')
                    window[KT_HOTKEY(block_num)].update('Press keys now')
                    threading.Thread(target=record_hotkey_thread, args=(window, block_num), daemon=True).start()
                    threading.Timer(15, record_timeout, args=(window, block_num)).start()      # give up if nothing is pressed
            elif event[0] == K_RECORDED:
                if recording_block != block_num:            # the timeout or a late result for a recording that's already finished
                    continue
                recording_block = None
                register_hotkeys()
                if not values[event]:
                    sg.popup_quick_message('Nothing captured - type the hotkey instead', font=(FONT_UI, 14), text_color='white', background_color='#b71c1c', keep_on_top=True)
                hotkey = values[event] or Block.active_blocks[block_num].hotkey
                Block.active_blocks[block_num].hotkey = hotkey
                if KT_RECORD(block_num) in window.key_dict:
                    window[KT_RECORD(block_num)].update('Rec', button_color=rec_colors())
                    window[KT_HOTKEY(block_num)].update(hotkey)
                G.dirty = True
        update_status(window)
    window.close()


# Hotkeys window images - 25 x 25
trash_icon = b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAMAAADzN3VRAAAAXVBMVEUAAADJoibJoifJoSbJoibIoiXKoCXJoibKoCbOpijIoibJoSfJoibJoibJoibIoSbWrSrIoSbJoSfNpijHoSXIoCjEnCfMoyjTqSnYrSrQqCjPpijmuSzJoifesytghzcEAAAAGHRSTlMA+cf92I1lhVjQzaOVy/Lf2LKvq0ozGhkawlE6AAAAnklEQVR4nM2RSQ6DMAxFbRLIwDy1xia5/zERSAUK6q6V+qR44SfFyTfAbzCN1rox783cld5XJCxUeV+6fDd1FKagVgKxxHo3oxPc2mtBceNxXUIqMIkS4qAoOQ1KCKmwbWxtQXg1kwUzG7DT3WSQzilkf2nsp1dTMXSxG+4/VUFItnNJh1HhGiqiQi7PC4rCLyQe6wF49Pqgf57Mt1gAAwEOREh/iwwAAAAASUVORK5CYII='

trash_icon_red = b'iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAMAAADzN3VRAAAASFBMVEUAAAD/AAD/AADrAAD/AAD/AADcAAD/AADtAAD3AADYAAD/AAD/AADwAADuAADuAAD6AADrAAD/AADOAAD/AACmAACtAAD/AADCW8QwAAAAF3RSTlMA/fnH2GWN3bGkhVru1Mq6uZOISjcaGe/TegUAAACDSURBVHiczZHtCsMgDEWTOKvWfrfbff83HYngHF3/bbCDYLjHqCjRb9huyvYeLiGEIFBEy6WawUJWrBqqOUZLuUgej9d2DmWxtcI1BzkIkp8x+wQ5mUw9esofjKcOHfm/NPny1useEff1ZK5eZ2JhHWWaGpNqh5Iac4/2oYX4aMy3eALVGAyXRSQ2kQAAAABJRU5ErkJggg=='

arrow_up_icon = b'iVBORw0KGgoAAAANSUhEUgAAABQAAAAUBAMAAAB/pwA+AAAAFVBMVEUAAAD///////////////////////9Iz20EAAAABnRSTlMA7+dzQjw0HakXAAAASklEQVR4nGNgwAlYA0AkE4gwFIYJMieKGUBF9T7wP4YwmY03/DY2YGBgYWDQu8PAsI8fLCp8gIHhjyFUH6MC3DAIoBKTBeQaHAAAlFUJ4B53P1AAAAAASUVORK5CYII='

arrow_down_icon = b'iVBORw0KGgoAAAANSUhEUgAAABQAAAAUBAMAAAB/pwA+AAAAGFBMVEUAAAD///////////////////////////8jfp1fAAAAB3RSTlMA7+dCdDxv5JkNzAAAAEtJREFUeJxjYMAJmA1AJBOI+PcBzoQAqjCNQbQxmKlnwMDA/BjMXOzMwGCixcDAyMDA4Chw5f0biLbDCp90YHrdS0AkC4jYx4nbAwDBQwuw1K+ENQAAAABJRU5ErkJggg=='


'''
M""MMMMM""M M#"""""""'M     dP                         dP       
M  MMMM' .M ##  mmmm. `M    88                         88       
M       .MM #'        .M    88d888b. .d8888b. .d8888b. 88  .dP  
M  MMMb. YM M#  MMMb.'YM    88'  `88 88'  `88 88'  `88 88888"   
M  MMMMb  M M#  MMMM'  M    88    88 88.  .88 88.  .88 88  `8b. 
M  MMMMM  M M#       .;M    dP    dP `88888P' `88888P' dP   `YP 
MMMMMMMMMMM M#########M
'''

# Hotkeys are registered in register_hotkeys() (the hotkey section near the top of the file) - with Windows' RegisterHotKey, keyboard.add_hotkey() elsewhere.


'''
M"""""`'"""`YM          oo          
M  mm.  mm.  M                      
M  MMM  MMM  M .d8888b. dP 88d888b. 
M  MMM  MMM  M 88'  `88 88 88'  `88 
M  MMM  MMM  M 88.  .88 88 88    88 
M  MMM  MMM  M `88888P8 dP dP    dP 
MMMMMMMMMMMMMM
'''

INSTANCE_PORT = 47322                # localhost port used to make sure only one copy of psghotkey runs
K_TRAY = '-TRAY-'                    # the tray icon's events
K_TRAY_MENU = '-TRAY MENU-'          # the tray icon was right-clicked
K_MIN_TO_TRAY = '-MINIMIZE TO TRAY-' # settings entry and right-click toggle: closing the card minimizes it to the tray
K_EXIT = 'Exit'
TRAY_TOOLTIP = f'{APP_NAME}  -  click for the window,  right-click for the menu'
K_QUIT_REQUEST = '-QUIT-REQUEST-'    # event sent to the window when a newer copy wants us to exit


# --- TRAY: the same block in every tray app (master copy in tray_app_template.pyw / tray_app_recipe.md) ---
try:
    from psgtray import SystemTray
except ImportError:                   # no tray icon - closing the window ends the program
    SystemTray = None


class Tray:
    icon = None                       # the psgtray SystemTray while it is shown
    use = True                        # closing the window minimizes to the tray (setting K_MIN_TO_TRAY, and psgtray is installed)


def tray_start(window, icon, tooltip):
    """ the tray icon, made in a thread (psgtray sleeps ~0.4 s while its own thread starts).  Click: window shown/hidden.  Right-click: our menu """
    def make():
        tray = SystemTray(['', [K_EXIT]], icon=icon, tooltip=tooltip[:127], single_click_events=True, window=window, key=K_TRAY)  # tips over 127 crash
        tray.key = K_TRAY                                                                            # psgtray makes it '-TRAY-1', '-TRAY-2'... for every later icon
        handlers = getattr(tray.tray_icon, '_message_handlers', {})                                  # Windows: pystray's own right-click menu is gray - use ours
        for msg, handler in list(handlers.items()):
            if getattr(handler, '__name__', '') == '_on_notify':                                      # the icon's mouse messages; 0x0205 = WM_RBUTTONUP
                handlers[msg] = lambda wparam, lparam, original=handler: window.write_event_value(K_TRAY_MENU, None) if lparam == 0x0205 else original(wparam, lparam)
        Tray.icon = tray
    if SystemTray and Tray.use and not Tray.icon:
        threading.Thread(target=make, daemon=True).start()


def tray_stop():
    """ call before window.close() - otherwise a dead icon sits in the tray until the mouse passes over it """
    if Tray.icon:
        Tray.icon.close()
        Tray.icon = None


def tray_menu(window):
    """ the window's right-click menu at the mouse.  Windows only closes a tray menu on a click elsewhere if its program is in front """
    x, y = window.TKroot.winfo_pointerxy()
    ctypes.windll.user32.SetForegroundWindow(window.TKroot.winfo_id())
    window.TKRightClickMenu.tk_popup(x, y)


def window_hidden(window):
    return window.TKroot.state() == 'withdrawn'


def window_show(window):
    window.un_hide()
    window.bring_to_front()
    window.force_focus()


def tray_event(window, event, values):
    """ handles the tray's own events; True when it did.  Click toggles the window, right-click opens the menu """
    if event == K_TRAY:
        if values[K_TRAY] == sg.EVENT_SYSTEM_TRAY_ICON_ACTIVATED:
            window_show(window) if window_hidden(window) else window.hide()
        elif values[K_TRAY] == K_EXIT:                                                               # pystray's gray menu - only if the right-click hook failed
            window.write_event_value(K_EXIT, None)
        return True
    if event == K_TRAY_MENU:
        tray_menu(window)
        return True
    return False


def style_menus(window):
    """ tk draws menus Windows-gray; recolor every right-click menu (PySimpleGUI makes one per element) and its sub-menus: flat, theme colors """
    def style(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Menu):
                child.configure(bg=sg.theme_background_color(), fg=sg.theme_text_color(), activebackground=C_MENU_SEL, activeforeground='#ffffff',
                                disabledforeground='#8a93a3', bd=0, activeborderwidth=1, relief='flat', font=FONT_MENU)
            style(child)
    style(window.TKroot)
# --- end TRAY ---


# --- STARTUP: start with Windows, hidden in the tray - the same block in every tray app (master copy in tray_app_template.pyw / tray_app_recipe.md) ---
# The program supplies APP_NAME (the shortcut's name) and its icon (PNG base64) to set_startup().  Off to start: the user ticks it once per PC.
START_IN_TRAY = '--tray' in sys.argv[1:]                          # started by the Startup shortcut: stay hidden in the tray
K_STARTUP = '-START WITH WINDOWS-'                                # right-click toggle: the shortcut in this user's Startup folder


def startup_link():
    """ the shortcut in this user's Startup folder that starts the program with Windows, hidden in the tray """
    return os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', f'{APP_NAME}.lnk')


def startup_on():
    return sg.running_windows() and os.path.exists(startup_link())


def set_startup(on, icon=None):
    """ right-click > Start with Windows, in the tray: make the shortcut (pythonw "<this file>" --tray) or remove it.  icon = the program's PNG
        (base64): it goes beside the program's settings as <APP_NAME>.ico, because a shortcut takes its icon from a file.  Returns '' or why it failed """
    path = startup_link()
    try:
        if not on:
            if os.path.exists(path):
                os.remove(path)
            return ''
        exe = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')                     # no console window
        exe = exe if os.path.isfile(exe) else sys.executable
        script = os.path.abspath(__file__)
        ico = ''
        if icon:
            png = base64.b64decode(icon)
            ico = os.path.join(os.path.dirname(sg.user_settings_filename()), f'{APP_NAME}.ico')
            width, height = struct.unpack('>II', png[16:24])
            os.makedirs(os.path.dirname(ico), exist_ok=True)
            with open(ico, 'wb') as f:                                                           # an .ico may hold the PNG as it is (Windows Vista and later)
                f.write(struct.pack('<HHHBBBBHHII', 0, 1, 1, width % 256, height % 256, 0, 0, 1, 32, len(png), 22) + png)
        q = lambda s: s.replace("'", "''")                                                       # inside a PowerShell '...' string
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(path)}');$s.TargetPath='{q(exe)}';$s.Arguments='\"{q(script)}\" --tray';"
              f"$s.WorkingDirectory='{q(os.path.dirname(script))}';" + (f"$s.IconLocation='{q(ico)}';" if ico else '') + '$s.Save()')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], creationflags=0x08000000, timeout=30, check=True, capture_output=True)   # no window
        return '' if os.path.exists(path) else 'Windows did not make the shortcut'
    except Exception as e:
        return str(e) or type(e).__name__
# --- end STARTUP ---


def make_menu():
    """ the card's right-click menu - the tray icon's right-click opens the same one.  A check mark on the current choices """
    tick = lambda on: '✓ ' if on else '    '                           # every label starts with a tick or the same width of spaces, so they line up
    theme = lambda n: f'{tick(n == G.theme)}{n}::{KT_THEME(n)}'
    tray = [f'{tick(Tray.use)}Minimize to tray when closed::{K_MIN_TO_TRAY}'] if SystemTray else []
    tray += [f'{tick(startup_on())}Start with Windows, in the tray::{K_STARTUP}'] if SystemTray and sg.running_windows() and not DEMO else []
    return ['', [f'    {APP_NAME} {VERSION}::Version', '---',                                     # the same layout in every tray app (tray_app_recipe.md)
                 f'    Hotkeys...::{K_HOTKEYS}', '---', *tray,
                 '    Theme', [theme(n) for n in sorted(THEMES, key=lambda n: is_light(THEMES[n]['card']))],        # dark, then light
                 f'    Brightness{f" ({bright_text(G.bright)})" if G.bright else ""}...::{K_BRIGHT}',
                 '---', '    Edit Me::Edit Me', f'    Version {VERSION}::Version', f'    Exit::{K_EXIT}']]


def apply_menu(window):
    menu = make_menu()
    for element in window.element_list():
        element.set_right_click_menu(menu, propogate_to_window=True)
    style_menus(window)
    theme_menus(window)


def menu_colors():
    """ The right-click menus' background and text: the card's own colors (background lifted a touch), so the menus match the theme """
    T = theme_colors()
    return mix(T['card'], T['text'], 0.04), T['text']


def theme_swatch(name):
    """ A tiny card in a theme's colors (card, a line of text, a dim line) shown beside its name in the Theme menu.  Made once and kept - tk drops images nobody holds """
    if (name, G.bright) not in G.swatches:                                                      # a set per Brightness level: the chips show what you'd get
        T, z = theme_colors(name), max(1.0, G.window.TKroot.winfo_fpixels('1i') / 96) * 4           # drawn 4x and shrunk, so the edges are smooth
        im = Image.new('RGBA', (round(34 * z), round(20 * z)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=5 * z, fill=T['card'], outline=C_SWATCH_EDGE, width=round(z))
        d.rounded_rectangle((6 * z, 5.5 * z, 25 * z, 9 * z), radius=1.5 * z, fill=T['text'])
        d.rounded_rectangle((6 * z, 12 * z, 17 * z, 14.5 * z), radius=1.2 * z, fill=T['dim'])
        buf = io.BytesIO()
        im.resize((round(im.width / 4), round(im.height / 4)), Image.LANCZOS).save(buf, 'PNG')
        G.swatches[(name, G.bright)] = tk.PhotoImage(master=G.window.TKroot, data=base64.b64encode(buf.getvalue()))
    return G.swatches[(name, G.bright)]


def theme_menus(window):
    """ After the TRAY block's style_menus(): lift every menu's background a touch off the window's, and put a color chip beside each theme name,
        the light themes in a second column - the widgets' Theme menu """
    bg, fg = menu_colors()

    def dress(menu):
        try:
            menu.configure(bg=bg, fg=fg)
        except tk.TclError:                                             # a menu PySimpleGUI has already replaced and destroyed
            return
        first_light = True
        for i in range(menu.index('end') + 1 if menu.index('end') is not None else 0):
            name = menu.entrycget(i, 'label').lstrip('✓ ') if menu.type(i) == 'command' else None
            if name in THEMES:
                menu.entryconfigure(i, image=theme_swatch(name), compound='left')
                if first_light and is_light(THEMES[name]['card']):
                    menu.entryconfigure(i, columnbreak=1)                     # the light themes get a column of their own
                    first_light = False
        for child in menu.winfo_children():
            if isinstance(child, tk.Menu):
                dress(child)

    for child in window.TKroot.winfo_children():
        if isinstance(child, tk.Menu):
            dress(child)


def ui_colors():
    """ The theme's five colors (at the Brightness setting) and what the Hotkeys window works out from them: light or not, the title strip,
        input boxes and faint text """
    T = theme_colors()
    light = is_light(T['card'])
    return dict(T, light=light, strip=mix(T['card'], T['border'], 0.4 if light else 0.3), input='#ffffff' if light else T['track'], faint=mix(T['dim'], T['card'], 0.35))


def apply_sg_theme():
    """ The chosen theme (at its Brightness) as the PySimpleGUI theme: the Hotkeys window and every popup are made with it """
    T = ui_colors()
    sg.theme_add_new(APP_NAME, {'BACKGROUND': T['card'], 'TEXT': T['text'], 'INPUT': T['input'], 'TEXT_INPUT': T['text'], 'SCROLL': T['border'] if T['light'] else T['track'],
                                'BUTTON': ('#ffffff', C_MENU_SEL), 'PROGRESS': (C_ACCENT, T['track']), 'BORDER': 1, 'SLIDER_DEPTH': 0, 'PROGRESS_DEPTH': 0})
    sg.theme(APP_NAME)


def scaled_png(b64, px):
    """ A base64 PNG made px design pixels square, times the display scaling - the program is dpi aware, so tk shows pictures pixel for pixel """
    key = (b64, px, G.scale)
    if key not in G.images:
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGBA').resize((round(px * G.scale), round(px * G.scale)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'PNG')
        G.images[key] = base64.b64encode(buf.getvalue())
    return G.images[key]


# ------------------------------------------------------------ The card ------------------------------------------------------------

def rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mix(c1, c2, f):
    """ Blend two hex colors, f=0 -> c1, f=1 -> c2 """
    return '#%02x%02x%02x' % tuple(round(a + (b - a) * f) for a, b in zip(rgb(c1), rgb(c2)))


def is_light(color):
    """ True for a light color - a light card gets darker status colors """
    r, g, b = rgb(color)
    return 0.299 * r + 0.587 * g + 0.114 * b > 140


def status_color(kind, T, text=False):
    """ 'good' green / 'warn' amber / 'bad' red for the card's theme: darker on a light card, darker still for text (amber text is hard to read on white) """
    color = {'good': C_GOOD, 'warn': C_WARN, 'bad': C_BAD}[kind]
    return mix(color, '#000000', 0.3 if text else 0.18) if is_light(T['card']) else color


def accent(T):
    return mix(C_ACCENT, '#000000', 0.18) if is_light(T['card']) else C_ACCENT


def font(bold, px):
    """ A Segoe UI (Windows) / DejaVu (Linux) font of px pixels, cached """
    key = (bold, px)
    if key not in G.fonts:
        f = None
        for name in FONT_NAMES[bold]:
            try:
                f = ImageFont.truetype(name, px)
                break
            except OSError:
                continue
        if f is None:
            try:
                f = ImageFont.load_default(size=px)
            except TypeError:
                f = ImageFont.load_default()
        G.fonts[key] = f
    return G.fonts[key]


def fit(d, text, fnt, width):
    """ text shortened with an ellipsis so it fits in width pixels """
    if d.textlength(text, font=fnt) <= width:
        return text
    while text and d.textlength(text + '…', font=fnt) > width:
        text = text[:-1]
    return text + '…'


def pretty_hotkey(hotkey):
    """ How the card shows a hotkey:  'ctrl+alt+p' -> 'Ctrl+Alt+P',  'print screen' -> 'Print Screen' """
    return '+'.join(p.title() if len(p) > 1 else p.upper() for p in hotkey.replace('++', '+plus').split('+'))


def short_command(value):
    """ A launch command as the card shows it - the program's file name and its arguments:   pythonw.exe "<folder>/psgsnip.pyw" --snip  ->  psgsnip.pyw --snip """
    try:
        parts = [p.strip('"') for p in shlex.split(value.strip(), posix=False)]
    except ValueError:
        return value.strip()
    if len(parts) > 1 and os.path.basename(parts[0]).lower() in PYTHON_NAMES:
        parts = parts[1:]                                               # the script is the program, not the interpreter that runs it
    return ' '.join([os.path.basename(parts[0]) or parts[0]] + parts[1:]) if parts else ''


def what_it_does(action, value):
    """ The card's TEXT OR PROGRAM cell: the text it types in quotes (¶ for each new line), or the program it runs """
    return short_command(value) if action == ACTION_LAUNCH else '“' + value.replace('\r', '').replace('\n', '¶') + '”'


def set_status(text, kind=None):
    """ A message for the card's bottom line, shown while the mouse isn't over one of its parts.  kind None, 'good' or 'bad' colors it """
    G.status = (text, kind)


def shown_rows():
    return min(MAX_ROWS, max(1, len(hotkey_info)))


def card_height():
    return ROW_TOP + shown_rows() * ROW_H + 32 + RECENT_N * RECENT_H + 6 + FOOT_H


def summary():
    """ The bottom line when the mouse isn't over anything and there's no message """
    if DEMO:
        return 'demo - example hotkeys, nothing is registered   ·   right-click for the menu'
    n = len(hotkey_info)
    if not n:
        return 'Click the gear to add your first hotkey'
    if n > MAX_ROWS:
        return f'Hotkeys {G.top + 1}-{G.top + MAX_ROWS} of {n} - the mouse wheel scrolls   ·   click one to edit it'
    return 'Click a hotkey to edit it   ·   right-click for the menu'


def hint(part):
    """ What a click will do - shown in the bottom line while the mouse is over that part """
    if part == 'gear':
        return 'Hotkeys - add, change or remove them'
    if part == 'close':
        return 'Minimize to tray   (Esc)' if Tray.use else f'Close {APP_NAME} - the hotkeys stop working   (Esc)'
    if part == 'empty':
        return 'Click to add your first hotkey'
    if isinstance(part, tuple) and part[1] < len(hotkey_info):
        hotkey = list(hotkey_info)[part[1]]
        if hotkey in G.bad:
            return f"{pretty_hotkey(hotkey)} isn't working - a bad key name, or another program has it"
        return f'Click to edit {pretty_hotkey(hotkey)}'
    return summary()


def draw_gear(d, cx, cy, r, color, hole):
    """ 8-tooth gear: a star-shaped polygon with flat tooth tops, and a hole in the middle """
    pts = []
    for i in range(32):
        a = math.radians(i * 360 / 32)
        rr = r if (i % 4) in (0, 1) else r * 0.72
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)
    d.ellipse((cx - r * 0.33, cy - r * 0.33, cx + r * 0.33, cy + r * 0.33), fill=hole)


def render():
    """ Draw the whole card and return it as PNG bytes.  Drawn at 2x and shrunk, so every edge is antialiased.  Also fills G.hits """
    s = G.scale
    k = s * 2
    T = theme_colors()                                                  # the theme at the Brightness setting
    H = G.height = card_height()
    W_px, H_px = round(CARD_W * k), round(H * k)
    im = Image.new('RGBA', (W_px, H_px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W_px - 1, H_px - 1), radius=(RADIUS if SEE_THROUGH else 0) * k, fill=T['card'], outline=T['border'], width=max(1, round(k)))
    line = lambda y: d.line((14 * k, y * k, (CARD_W - 14) * k, y * k), fill=T['track'], width=max(1, round(k)))
    big, small, small_bold = font(True, round(13 * k)), font(False, round(12 * k)), font(True, round(12 * k))
    head_color = mix(T['dim'], T['card'], 0.2)
    hotkeys = list(hotkey_info)
    n, refused = len(hotkeys), len(G.bad & set(hotkeys))
    hits = []
    # ---- header: status dot, name, version ....... how many work, gear, close
    d.ellipse((12 * k, 17 * k, 20 * k, 25 * k), fill=status_color('bad' if refused else 'good', T) if n else T['dim'])
    d.text((27 * k, BTN_Y * k), APP_NAME.upper(), font=big, fill=T['dim'], anchor='lm')
    version_x = 27 * k + d.textlength(APP_NAME.upper(), font=big) + 7 * k
    d.text((version_x, (BTN_Y + 1) * k), f'v{VERSION}', font=small, fill=mix(T['dim'], T['card'], 0.4), anchor='lm')
    count = f'{n - refused} of {n} working' if refused else f'{n} active' if n else 'none yet'
    d.text(((GEAR_X - 20) * k, (BTN_Y + 1) * k), count, font=small, fill=status_color('warn', T, text=True) if refused else T['dim'], anchor='rm')
    for part, cx in (('gear', GEAR_X), ('close', CLOSE_X)):
        hits.append((cx - BTN_R, BTN_Y - BTN_R, cx + BTN_R, BTN_Y + BTN_R, part))
        hot = G.hover == part
        if hot:
            d.ellipse(((cx - BTN_R) * k, (BTN_Y - BTN_R) * k, (cx + BTN_R) * k, (BTN_Y + BTN_R) * k), fill=C_CLOSE if part == 'close' else mix(T['text'], T['card'], 0.82))
        color = T['text'] if hot else mix(T['dim'], T['card'], 0.25)
        if part == 'gear':
            draw_gear(d, cx * k, BTN_Y * k, 6.5 * k, color, mix(T['text'], T['card'], 0.82) if hot else T['card'])
        else:
            r = 4.5 * k
            d.line((cx * k - r, BTN_Y * k - r, cx * k + r, BTN_Y * k + r), fill=color, width=max(1, round(1.6 * k)))
            d.line((cx * k - r, BTN_Y * k + r, cx * k + r, BTN_Y * k - r), fill=color, width=max(1, round(1.6 * k)))
    line(HEAD_H)
    # ---- column headings
    head_y = (HEAD_H + COLS_H / 2 + 2) * k
    for x, text in ((COL_KEY, 'HOTKEY'), (COL_ACTION, 'ACTION'), (COL_VALUE, 'TEXT OR PROGRAM')):
        d.text((x * k, head_y), text, font=small_bold, fill=head_color, anchor='lm')
    # ---- one row per hotkey, MAX_ROWS of them (the wheel scrolls); a fired one glows in the accent color
    if not n:
        hits.append((8, ROW_TOP, CARD_W - 8, ROW_TOP + ROW_H, 'empty'))
        hot = G.hover == 'empty'
        if hot:
            d.rounded_rectangle((8 * k, (ROW_TOP + 1) * k, (CARD_W - 8) * k, (ROW_TOP + ROW_H - 1) * k), radius=7 * k, fill=mix(T['text'], T['card'], 0.9))
        d.text((CARD_W / 2 * k, (ROW_TOP + ROW_H / 2) * k), 'No hotkeys yet - click here to add one', font=small, fill=T['text'] if hot else T['dim'], anchor='mm')
    for i in range(G.top, min(n, G.top + MAX_ROWS)):
        hotkey = hotkeys[i]
        action, value = hotkey_info[hotkey]
        y0 = ROW_TOP + (i - G.top) * ROW_H
        yc = (y0 + ROW_H / 2) * k
        part = ('row', i)
        hits.append((8, y0, CARD_W - 8, y0 + ROW_H, part))
        glow = hotkey in G.flash
        if glow or G.hover == part:
            d.rounded_rectangle((8 * k, (y0 + 1) * k, (CARD_W - 8) * k, (y0 + ROW_H - 1) * k), radius=7 * k,
                                fill=mix(accent(T), T['card'], 0.62) if glow else mix(T['text'], T['card'], 0.9))
        r = 4 * k
        d.ellipse((20 * k - r, yc - r, 20 * k + r, yc + r), fill=status_color('bad' if hotkey in G.bad else 'good', T))
        d.text((COL_KEY * k, yc), fit(d, pretty_hotkey(hotkey), big, (COL_ACTION - COL_KEY - 10) * k), font=big, fill=T['text'], anchor='lm')
        d.text((COL_ACTION * k, yc), ACTION_SHORT.get(action, action), font=small, fill=T['dim'], anchor='lm')
        d.text((COL_VALUE * k, yc), fit(d, what_it_does(action, value), small, (CARD_W - 18 - COL_VALUE) * k), font=small, fill=T['text'], anchor='lm')
    if n > MAX_ROWS:                                                    # a thin scroll bar: where the rows shown are in the whole list
        x, y0, y1 = (CARD_W - 5) * k, (ROW_TOP + 3) * k, (ROW_TOP + MAX_ROWS * ROW_H - 3) * k
        d.line((x, y0, x, y1), fill=T['track'], width=round(3 * k))
        d.line((x, y0 + (y1 - y0) * G.top / n, x, y0 + (y1 - y0) * (G.top + MAX_ROWS) / n), fill=T['dim'], width=round(3 * k))
    # ---- RECENT: the last hotkeys that fired, newest first
    rows_end = ROW_TOP + shown_rows() * ROW_H
    line(rows_end + 6)
    d.text((18 * k, (rows_end + 20) * k), 'RECENT', font=small_bold, fill=head_color, anchor='lm')
    if not G.recent:
        d.text((18 * k, (rows_end + 32 + RECENT_H / 2) * k), 'Nothing yet - each hotkey shows up here when you press it', font=small, fill=T['dim'], anchor='lm')
    for i, (when, hotkey, what, error) in enumerate(G.recent):
        yc = (rows_end + 32 + (i + 0.5) * RECENT_H) * k
        d.text((18 * k, yc), when, font=small, fill=T['dim'], anchor='lm')
        x = 78 * k
        for text, fnt, color in ((pretty_hotkey(hotkey), small_bold, T['text']), ('→', small, T['dim'])):
            d.text((x, yc), text, font=fnt, fill=color, anchor='lm')
            x += d.textlength(text, font=fnt) + 8 * k
        text, color = (f'could not run it: {error}', status_color('bad', T, text=True)) if error else (what, T['text'])
        d.text((x, yc), fit(d, text, small, (CARD_W - 18) * k - x), font=small, fill=color, anchor='lm')
    # ---- bottom line: what a click on the part under the mouse will do, else a message, else a summary
    foot_y = rows_end + 32 + RECENT_N * RECENT_H + 6
    line(foot_y)
    if G.hover:
        text, color = hint(G.hover), T['text']
    elif G.status[0]:
        text, color = G.status[0], status_color(G.status[1], T, text=True) if G.status[1] else T['text']
    else:
        text, color = summary(), T['dim']
    d.text((CARD_W / 2 * k, (foot_y + FOOT_H / 2 - 1) * k), fit(d, text, small, (CARD_W - 28) * k), font=small, fill=color, anchor='mm')
    G.hits = hits
    im = im.resize((round(CARD_W * s), round(H * s)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def redraw(window):
    """ Draw the card again.  When its height changed (hotkeys added or removed), keep all of it on the screen """
    height = G.height
    window[K_IMAGE].update(data=render())
    if G.height != height and not window_hidden(window):
        window.refresh()
        keep_on_screen(window)


def part_at(x, y):
    """ The part of the card at widget pixel (x, y): ('row', i), 'empty', 'gear', 'close' or None """
    x, y = x / G.scale, y / G.scale
    for x0, y0, x1, y1, part in G.hits:
        if part in ('gear', 'close'):
            if math.hypot(x - (x0 + x1) / 2, y - (y0 + y1) / 2) <= BTN_R:
                return part
        elif x0 <= x <= x1 and y0 <= y <= y1:
            return part
    return None


def bind_mouse(window):
    """ Hover and clicks on the card's parts, the wheel for its rows, and where it was dragged to.  grab_anywhere does the dragging; these
        bindings are added alongside it (add='+') """
    widget = window[K_IMAGE].Widget

    def motion(e):
        part = part_at(e.x, e.y)
        if part != G.hover:
            window.write_event_value(K_HOVER, part)

    def press(e):
        G.press = (e.x_root, e.y_root, part_at(e.x, e.y))

    def release(e):
        p, G.press = G.press, None
        if not p:
            return
        if math.hypot(e.x_root - p[0], e.y_root - p[1]) >= 4:
            window.write_event_value(K_MOVED, None)                     # a drag of the card, not a click
        elif p[2] is not None and part_at(e.x, e.y) == p[2]:
            window.write_event_value(K_CLICK, p[2])

    widget.bind('<Motion>', motion, add='+')
    widget.bind('<Leave>', lambda e: window.write_event_value(K_HOVER, None) if G.hover else None, add='+')
    widget.bind('<ButtonPress-1>', press, add='+')
    widget.bind('<ButtonRelease-1>', release, add='+')
    widget.bind('<MouseWheel>', lambda e: window.write_event_value(K_SCROLL, -1 if e.delta > 0 else 1), add='+')       # Windows
    widget.bind('<Button-4>', lambda e: window.write_event_value(K_SCROLL, -1), add='+')                               # Linux wheel
    widget.bind('<Button-5>', lambda e: window.write_event_value(K_SCROLL, 1), add='+')


def card_event(window, event, values):
    """ The card's own events - hover, the wheel, a drag, a hotkey firing, a glow ending.  True when it was one of them """
    if event == K_HOVER:
        G.hover = values[K_HOVER]
    elif event == K_SCROLL:
        top = max(0, min(len(hotkey_info) - MAX_ROWS, G.top + values[K_SCROLL]))
        if top == G.top:
            return True
        G.top, G.hover = top, None                                      # other rows are under the mouse now - the next move finds which
    elif event == K_MOVED:
        get_settings().set(K_LOCATION, list(window.current_location()))
        return True
    elif event == K_HOTKEY_FIRED:
        hotkey, error = values[K_HOTKEY_FIRED]
        action, value = hotkey_info.get(hotkey, (ACTION_TEXT, ''))
        what = f'ran {short_command(value)}' if action == ACTION_LAUNCH else f'typed {what_it_does(action, value)}'
        G.recent.appendleft((time.strftime('%H:%M:%S'), hotkey, what, error))
        G.flash[hotkey] = time.time()
        window.timer_start(FLASH_MS, key=K_FLASH_OFF, repeating=False)
    elif event == K_FLASH_OFF:
        G.flash = {hotkey: t for hotkey, t in G.flash.items() if time.time() - t < FLASH_MS / 1000 - 0.1}
    else:
        return False
    redraw(window)
    return True


def keep_going(window, event, values):
    """ While the Brightness panel is open the card keeps hovering, scrolling and showing the hotkeys as they fire.  Anything else closes the panel
        and goes to the main loop """
    return card_event(window, event, values)


def show_card(window):
    """ The card, drawn fresh, in front and with the keyboard (for Esc).  Hiding a window can lose 'keep on top' - it is set again """
    G.hover = None
    redraw(window)
    if window_hidden(window):
        window.un_hide()
    window.set_alpha(1)
    window.keep_on_top_set()
    window.bring_to_front()
    window.force_focus()


def hide_card(window):
    window.hide()
    G.hover = None
    set_status('')


def work_area(x, y, nearest=True):
    """ (left, top, right, bottom) of the work area (the screen minus the taskbar) of the monitor at screen point x, y.  When the point is on no
        monitor: the nearest one's - or None when nearest is False """
    if sys.platform == 'win32':
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT), ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]
        user32 = ctypes.windll.user32
        user32.MonitorFromPoint.argtypes, user32.MonitorFromPoint.restype = [wintypes.POINT, wintypes.DWORD], wintypes.HMONITOR
        user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
        monitor = user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2 if nearest else 0)            # MONITOR_DEFAULTTONEAREST / MONITOR_DEFAULTTONULL
        if not monitor:
            return None
        info = MonitorInfo(cbSize=ctypes.sizeof(MonitorInfo))
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom
    w, h = G.window.TKroot.winfo_screenwidth(), G.window.TKroot.winfo_screenheight()
    return (0, 0, w, h) if nearest or (0 <= x < w and 0 <= y < h) else None


def keep_on_screen(window, x=None, y=None):
    """ Move the card to x, y (where it is when not given) - but with all of it on the screen it is on """
    if x is None:
        x, y = window.current_location()
    w, h = window.size
    left, top, right, bottom = work_area(x + w // 2, y + h // 2)
    window.move(max(left, min(x, right - w)), max(top, min(y, bottom - h)))
    window.refresh()                                    # done now: a keep_on_top_set() / bring_to_front() before the move happens undoes it (Windows)


def place_card(window):
    """ Where the card was left last time if that is still on a screen, else the bottom right corner of the main screen, over the tray """
    window.refresh()
    spot = get_settings().get(K_LOCATION, None)
    if isinstance(spot, (list, tuple)) and len(spot) == 2 and work_area(spot[0] + 40, spot[1] + 20, nearest=False):
        keep_on_screen(window, *spot)
    else:
        w, h = window.size
        left, top, right, bottom = work_area(0, 0)
        keep_on_screen(window, right - w - round(12 * G.scale), bottom - h - round(12 * G.scale))


def claim_single_instance(port, timeout=5.0):
    """ If a previous copy of this program is listening on `port`, tell it to QUIT and wait for it to let go of the port.
        Returns (listening socket this copy now owns - pass it to instance_listener - or None if the port couldn't be claimed,
                 True if a running copy was told to quit) """
    replaced = False
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1.0) as old:
            replaced = True
            old.sendall(b'QUIT')
            old.settimeout(timeout)
            try:
                old.recv(16)                             # the old copy answers OK just before it exits
            except OSError:
                pass
    except OSError:
        pass                                             # nobody listening - we're the only copy
    deadline = time.time() + timeout
    while True:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            srv.bind(('127.0.0.1', port))
            srv.listen(1)
            return srv, replaced
        except OSError:
            srv.close()
            if time.time() > deadline:
                return None, replaced
            time.sleep(0.2)


def instance_listener(srv, window, key):
    """ Thread: when a newer copy of the program connects and says QUIT, send `key` to the window's event loop so it can exit cleanly """
    while True:
        try:
            conn, _ = srv.accept()
        except OSError:
            return                                       # socket closed - we're exiting
        with conn:
            try:
                if conn.recv(16).startswith(b'QUIT'):
                    conn.sendall(b'OK')
                    window.write_event_value(key, None)
            except OSError:
                pass


# --- BRIGHTNESS: the same block in every card widget (master copy in modern_widget_recipe.md) - the program darkens or lightens its own theme ---
# Right-click > Brightness... opens a small panel under the card with a slider, and the card changes as the knob moves.  theme_colors() is what the card,
# its menu and the Theme chips are drawn with: the theme at the chosen level, its text kept readable.  The program supplies redraw(window),
# font(bold, px), is_light(), RADIUS, TRANSPARENT, THEMES and G.theme / G.scale / G.bright / G.tuned.
BRIGHT_LEVELS = list(range(-80, 51, 5))                           # the slider's stops, darkest first: -80 = much darker, 0 = as designed, 50 = lighter
K_BRIGHT = '-BRIGHTNESS-'                                         # settings-file entry, and the right-click item that opens the panel
K_PANEL_IMAGE, K_PANEL_VALUE, K_PANEL_STEP = '-PANEL IMAGE-', '-PANEL VALUE-', '-PANEL STEP-'      # values: the new level / +1 or -1 stop
K_PANEL_HOVER, K_PANEL_CLICK = '-PANEL HOVER-', '-PANEL CLICK-'   # values: 'track' | 'reset' | 'done' | None
K_PANEL_DONE, K_PANEL_CANCEL = '-PANEL DONE-', '-PANEL CANCEL-'   # Enter / Escape
PANEL_W, PANEL_H = 270, 114                                       # the panel, in design pixels
TRACK_X0, TRACK_X1, TRACK_Y, TRACK_H = 20, PANEL_W - 20, 52, 10
PILL_W, PILL_H, PILL_Y = 70, 24, 90                               # Reset (left) and Done (right); PILL_Y is their middle
C_PANEL_DONE = '#2a62a8'                                          # the Done button


def channels(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def shade(c1, c2, f):
    """c1 moved f of the way toward c2"""
    return '#%02x%02x%02x' % tuple(round(a + (b - a) * f) for a, b in zip(channels(c1), channels(c2)))


def tune(color, level, light, line=False):
    """A card / border / track color at a Brightness level.  Dark themes: the brightness is scaled - darker is deeper, lighter more vivid, the hue kept;
       lines darken less, so the border and the gauge track still show at -80.  Light themes: darker turns gently gray (at most 32%), lighter fades to white"""
    if light and level > 0:
        return shade(color, '#ffffff', level / 100)
    f = 1 + level / (250 if light else 100)
    if line and level < 0 and not light:
        f **= 0.6
    return '#%02x%02x%02x' % tuple(min(255, round(v * f)) for v in channels(color))


def luminance(color):
    """WCAG relative luminance, 0 = black .. 1 = white"""
    return sum(w * (v / 3294.6 if v <= 10.31 else ((v / 255 + 0.055) / 1.055) ** 2.4) for w, v in zip((0.2126, 0.7152, 0.0722), channels(color)))


def readable(fg, bg, ratio, pole):
    """fg moved toward pole (white on a dark card, black on a light one) just far enough to have ratio contrast with bg"""
    lb = luminance(bg)
    for i in range(26):
        c = shade(fg, pole, i / 25)
        lf = luminance(c)
        if (max(lf, lb) + 0.05) / (min(lf, lb) + 0.05) >= ratio:
            return c
    return pole


def theme_colors(name=None):
    """A theme's five colors at the Brightness setting (the chosen theme if no name) - text keeps 7:1 contrast with the card, dim 4.5:1"""
    name = name if name in THEMES else G.theme if G.theme in THEMES else 'Toybox'
    if (name, G.bright) not in G.tuned:
        T = THEMES[name]
        if G.bright:
            light, level = is_light(T['card']), G.bright
            card, pole = tune(T['card'], level, light), '#000000' if light else '#ffffff'
            T = {'card': card, 'border': tune(T['border'], level, light, True), 'track': tune(T['track'], level, light, True),
                 'text': readable(T['text'], card, 7, pole), 'dim': readable(T['dim'], card, 4.5, pole)}
        G.tuned[(name, G.bright)] = T
    return G.tuned[(name, G.bright)]


def bright_text(level):
    return 'as designed' if level == 0 else f'{level:+d}%'.replace('-', '\u2212')


def knob_x(level):
    """Design-pixel x of the knob at a level: the middle of that level's band on the track"""
    return TRACK_X0 + (BRIGHT_LEVELS.index(level) + 0.5) * (TRACK_X1 - TRACK_X0) / len(BRIGHT_LEVELS)


def level_at(x):
    """The level whose band is under panel pixel x"""
    i = int((x / G.scale - TRACK_X0) / (TRACK_X1 - TRACK_X0) * len(BRIGHT_LEVELS))
    return BRIGHT_LEVELS[max(0, min(len(BRIGHT_LEVELS) - 1, i))]


def panel_part(x, y):
    """'track', 'reset', 'done' or None at panel pixel (x, y)"""
    x, y = x / G.scale, y / G.scale
    if TRACK_X0 - 10 <= x <= TRACK_X1 + 10 and abs(y - TRACK_Y) <= 14:
        return 'track'
    if abs(y - PILL_Y) <= PILL_H / 2:
        if 18 <= x <= 18 + PILL_W:
            return 'reset'
        if PANEL_W - 18 - PILL_W <= x <= PANEL_W - 18:
            return 'done'
    return None


def render_panel(hover):
    """The Brightness panel, drawn like the card and in its colors (so it changes too).  The track shows the card's own color at every level, darkest
       on the left; the knob sits on the one in use, the tick under the track marks 'as designed'"""
    s = G.scale
    k = s * 2
    T, base = theme_colors(), THEMES.get(G.theme, THEMES['Toybox'])
    light = is_light(base['card'])
    W, H = round(PANEL_W * k), round(PANEL_H * k)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=(RADIUS if sg.running_windows() else 0) * k, fill=T['card'], outline=T['border'], width=max(1, round(k)))
    d.text((18 * k, 20 * k), 'BRIGHTNESS', font=font(True, round(13 * k)), fill=T['dim'], anchor='lm')
    d.text(((PANEL_W - 18) * k, 20 * k), bright_text(G.bright), font=font(True, round(13 * k)), fill=T['text'], anchor='rm')
    x0, x1, y0, y1 = TRACK_X0 * k, TRACK_X1 * k, (TRACK_Y - TRACK_H / 2) * k, (TRACK_Y + TRACK_H / 2) * k
    strip = Image.new('RGBA', (round(x1 - x0), round(y1 - y0)))                       # a band per level, in the card color at that level
    band = strip.width / len(BRIGHT_LEVELS)
    for i, level in enumerate(BRIGHT_LEVELS):
        ImageDraw.Draw(strip).rectangle((round(i * band), 0, round((i + 1) * band), strip.height), fill=tune(base['card'], level, light))
    mask = Image.new('L', strip.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, strip.width - 1, strip.height - 1), radius=strip.height / 2, fill=255)
    im.paste(strip, (round(x0), round(y0)), mask)
    d.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) / 2, outline=T['dim'] if hover == 'track' else T['border'], width=max(1, round(k)))
    zx = knob_x(0) * k
    d.line((zx, y1 + 3 * k, zx, y1 + 7 * k), fill=T['dim'], width=max(1, round(1.2 * k)))
    kx, ky, r = knob_x(G.bright) * k, TRACK_Y * k, 9 * k                                # the knob, filled with the color in use
    d.ellipse((kx - r, ky - r, kx + r, ky + r), fill=T['card'], outline=T['text'], width=max(1, round(2 * k)))
    small = font(False, round(11 * k))
    d.text((x0, (TRACK_Y + 17) * k), 'darker', font=small, fill=T['dim'], anchor='lm')
    d.text((x1, (TRACK_Y + 17) * k), 'lighter', font=small, fill=T['dim'], anchor='rm')
    for part, px, fill, color in (('reset', 18, T['track'], T['text'] if G.bright else T['dim']), ('done', PANEL_W - 18 - PILL_W, C_PANEL_DONE, '#ffffff')):
        if hover == part:
            fill = shade(fill, '#ffffff', 0.15) if part == 'done' else shade(T['text'], T['card'], 0.78)
        d.rounded_rectangle((px * k, (PILL_Y - PILL_H / 2) * k, (px + PILL_W) * k, (PILL_Y + PILL_H / 2) * k), radius=PILL_H / 2 * k, fill=fill)
        d.text(((px + PILL_W / 2) * k, PILL_Y * k), part.capitalize(), font=font(True, round(12 * k)), fill=color, anchor='mm')
    im = im.resize((round(PANEL_W * s), round(PANEL_H * s)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def brightness_panel(card, keep_going):
    """Right-click > Brightness...: the panel under the card.  The card and the panel change as the knob moves (drag, click, arrow keys, mouse wheel,
       Home / End).  Done or Enter keeps the level, Escape puts back the one it had.  keep_going(card, event, values) handles the card's own events
       meanwhile (its timer, hover...) and returns False for one that should close the panel - a menu choice, the close x.  That event is returned so the
       main loop can handle it; None otherwise"""
    start = G.bright
    x, y = card.current_location()
    below, height = y + card.size[1] + 6, round(PANEL_H * G.scale)
    py = below if below + height <= card.TKroot.winfo_screenheight() else max(0, y - height - 6)    # under the card, or above it near the bottom
    panel = sg.Window('Brightness', [[sg.Image(data=render_panel(None), key=K_PANEL_IMAGE, background_color=TRANSPARENT, pad=(0, 0))]], no_titlebar=True,
                      keep_on_top=True, margins=(0, 0), element_padding=(0, 0), background_color=TRANSPARENT, location=(x, py), finalize=True,
                      transparent_color=TRANSPARENT if sg.running_windows() else None)  # no grab_anywhere: it would move the panel as the knob is dragged
    widget, mouse = panel[K_PANEL_IMAGE].Widget, {'drag': False, 'press': None, 'hover': None}

    def press(e):
        part = panel_part(e.x, e.y)
        if part == 'track':                                                             # the knob jumps to the mouse and follows it
            mouse['drag'] = True
            panel.write_event_value(K_PANEL_VALUE, level_at(e.x))
        else:
            mouse['press'] = (e.x_root, e.y_root, part, panel.TKroot.winfo_x(), panel.TKroot.winfo_y())

    def drag(e):
        p = mouse['press']
        if mouse['drag']:
            panel.write_event_value(K_PANEL_VALUE, level_at(e.x))
        elif p:                                                                         # anywhere off the track drags the panel
            panel.TKroot.geometry(f'+{p[3] + e.x_root - p[0]}+{p[4] + e.y_root - p[1]}')

    def release(e):
        if mouse['drag']:
            mouse['drag'] = False
            return
        p, mouse['press'] = mouse['press'], None
        if p and p[2] in ('reset', 'done') and math.hypot(e.x_root - p[0], e.y_root - p[1]) < 4:        # a click, not a drag of the panel
            panel.write_event_value(K_PANEL_CLICK, p[2])

    def hover(part):
        if part != mouse['hover']:
            mouse['hover'] = part
            panel.write_event_value(K_PANEL_HOVER, part)

    widget.bind('<ButtonPress-1>', press, add='+')
    widget.bind('<B1-Motion>', drag, add='+')
    widget.bind('<ButtonRelease-1>', release, add='+')
    widget.bind('<Motion>', lambda e: hover(panel_part(e.x, e.y)), add='+')
    widget.bind('<Leave>', lambda e: hover(None), add='+')
    widget.bind('<MouseWheel>', lambda e: panel.write_event_value(K_PANEL_STEP, 1 if e.delta > 0 else -1), add='+')   # Windows
    widget.bind('<Button-4>', lambda e: panel.write_event_value(K_PANEL_STEP, 1), add='+')                            # Linux wheel
    widget.bind('<Button-5>', lambda e: panel.write_event_value(K_PANEL_STEP, -1), add='+')
    for seq, n in (('<Left>', -1), ('<Down>', -1), ('<Right>', 1), ('<Up>', 1)):
        panel.TKroot.bind(seq, lambda e, n=n: panel.write_event_value(K_PANEL_STEP, n))
    panel.TKroot.bind('<Home>', lambda e: panel.write_event_value(K_PANEL_VALUE, BRIGHT_LEVELS[0]))
    panel.TKroot.bind('<End>', lambda e: panel.write_event_value(K_PANEL_VALUE, BRIGHT_LEVELS[-1]))
    panel.bind('<Return>', K_PANEL_DONE)
    panel.bind('<Escape>', K_PANEL_CANCEL)
    panel.force_focus()
    pending = None
    while True:
        win, event, values = sg.read_all_windows()
        if win is card:                                                                 # the card keeps going while the panel is open
            if keep_going(card, event, values):
                continue
            pending = (event, values)
            break
        if event in (sg.WINDOW_CLOSED, K_PANEL_CANCEL):
            G.bright = start
            break
        if event == K_PANEL_DONE or (event == K_PANEL_CLICK and values[event] == 'done'):
            break
        level = G.bright
        if event == K_PANEL_VALUE:
            level = values[event]
        elif event == K_PANEL_STEP:
            level = BRIGHT_LEVELS[max(0, min(len(BRIGHT_LEVELS) - 1, BRIGHT_LEVELS.index(G.bright) + values[event]))]
        elif event == K_PANEL_CLICK and values[event] == 'reset':
            level = 0
        if level != G.bright:
            G.bright = level
            redraw(card)
        panel[K_PANEL_IMAGE].update(data=render_panel(mouse['hover']))
    panel.close()
    redraw(card)
    return pending
# --- end BRIGHTNESS ---


def demo_settings():
    """ --demo: the example hotkeys into the demo's own settings file, and a few made-up lines for RECENT """
    save_hotkey_list(DEMO_HOTKEYS)
    for minutes, hotkey in ((3, 'ctrl+alt+p'), (11, 'ctrl+alt+n'), (26, 'ctrl+alt+t'), (42, 'ctrl+alt+p')):
        action, value = next((a, v) for h, a, v in DEMO_HOTKEYS if h == hotkey)
        what = f'ran {short_command(value)}' if action == ACTION_LAUNCH else f'typed {what_it_does(action, value)}'
        G.recent.append((time.strftime('%H:%M:%S', time.localtime(time.time() - minutes * 60)), hotkey, what, None))


def run():
    instance_sock, replaced_running_copy = (None, False) if DEMO else claim_single_instance(INSTANCE_PORT)    # a previous copy is told to exit (not by the demo)
    sg.set_options(dpi_awareness=True, font=(FONT_UI, 10))                            # dpi aware: the card is drawn at the screen's own scale, so it's sharp
    settings = get_settings()
    if DEMO:
        demo_settings()
    G.theme = settings.get(K_THEME, 'Toybox')
    G.theme = OLD_THEME_NAMES.get(G.theme, G.theme if G.theme in THEMES else 'Toybox')
    G.bright = settings.get(K_BRIGHT, 0)
    G.bright = G.bright if G.bright in BRIGHT_LEVELS else 0
    Tray.use = bool(SystemTray) and settings.get(K_MIN_TO_TRAY, True) and not DEMO
    apply_sg_theme()
    build_hotkey_dict()

    menu_bg, menu_fg = menu_colors()
    layout = [[sg.Image(data=render(), key=K_IMAGE, background_color=TRANSPARENT, pad=(0, 0))]]
    title = f'{APP_NAME} - demo' if DEMO else APP_NAME
    window = sg.Window(title, layout, no_titlebar=True, grab_anywhere=True, keep_on_top=True, margins=(0, 0), element_padding=(0, 0), background_color=TRANSPARENT,
                       transparent_color=TRANSPARENT if SEE_THROUGH else None, alpha_channel=0, icon=window_icon(), finalize=True, enable_close_attempted_event=True,
                       right_click_menu=make_menu(), right_click_menu_background_color=menu_bg, right_click_menu_text_color=menu_fg,
                       right_click_menu_selected_colors=('#ffffff', C_MENU_SEL), right_click_menu_font=FONT_MENU)
    G.window = G.main_window = window
    G.scale = max(1.0, window.TKroot.winfo_fpixels('1i') / 96)                         # 2.0 on a 200% Windows display
    style_menus(window)
    theme_menus(window)
    bind_mouse(window)
    window.bind('<Escape>', K_ESCAPE)

    tray_start(window, window_icon(), TRAY_TOOLTIP)
    if instance_sock:
        threading.Thread(target=instance_listener, args=(instance_sock, window, K_QUIT_REQUEST), daemon=True).start()

    if replaced_running_copy:                                   # the copy we replaced may hold the hotkeys for a few more seconds while it exits
        for _ in range(12):
            if not register_hotkeys():
                break
            time.sleep(0.5)
    refresh_main_window(window)                                 # registers the hotkeys and draws the card at the screen's scale
    place_card(window)
    if Tray.use:
        window.hide()                                           # lives in the tray - the card is only shown when asked for
        window.set_alpha(1)
        window.TKroot.after(8000, lambda: show_card(window) if window_hidden(window) and not Tray.icon else None)   # no icon came: the card shows
        for _ in range(0 if START_IN_TRAY else 30):             # the icon is made in a thread - give it a moment for the balloon (none at sign-in)
            if Tray.icon:
                Tray.icon.show_message(APP_NAME, 'Running in the tray.  Click the icon to see your hotkeys.')
                break
            time.sleep(0.1)
    else:
        show_card(window)

    pending = None                                              # a card event that came in while the Brightness panel was open
    while True:
        event, values = pending or window.read()
        pending = None
        if isinstance(event, str) and '::' in event:            # right-click menu items come back as 'label::key'
            event = event.split('::')[-1]
        if tray_event(window, event, values):                   # tray click shows / hides the card, right-click opens the menu
            if event == K_TRAY and not window_hidden(window):
                show_card(window)                               # drawn fresh, and on top again
            continue
        if card_event(window, event, values):                   # hover, wheel, drag, a hotkey firing
            continue
        part = values[K_CLICK] if event == K_CLICK else None

        if event in (sg.WIN_CLOSED, K_EXIT, K_QUIT_REQUEST):
            break

        if event in (K_ESCAPE, sg.WIN_CLOSE_ATTEMPTED_EVENT) or part == 'close':
            if not Tray.use:
                break
            hide_card(window)
        elif event == K_MIN_TO_TRAY:
            Tray.use = not Tray.use
            settings.set(K_MIN_TO_TRAY, Tray.use)
            tray_start(window, window_icon(), TRAY_TOOLTIP) if Tray.use else tray_stop()
            if window_hidden(window):
                show_card(window)                               # never hidden with no tray icon to bring it back
            set_status('Closing the card now minimizes it to the tray' if Tray.use else f'Closing the card now ends {APP_NAME} - the hotkeys stop', None if Tray.use else 'bad')
            apply_menu(window)
            redraw(window)
        elif event == K_STARTUP:
            error = set_startup(not startup_on(), window_icon())
            set_status(f'Start with Windows, in the tray: {"on" if startup_on() else "off"}' if not error else f'Start with Windows: {error}', 'bad' if error else 'good')
            apply_menu(window)
            redraw(window)
        elif event == K_HOTKEYS or part in ('gear', 'empty') or isinstance(part, tuple):
            G.hover = None
            redraw(window)
            hotkeys_window(focus=part[1] if isinstance(part, tuple) else None, card=window)     # returns when it closes.  OK / Apply refresh the card
        elif isinstance(event, str) and event.startswith(K_THEME):
            G.theme = event[len(K_THEME):]
            settings.set(K_THEME, G.theme)
            apply_sg_theme()
            redraw(window)
            apply_menu(window)
        elif event == K_BRIGHT:
            if window_hidden(window):
                show_card(window)
            pending = brightness_panel(window, keep_going)
            settings.set(K_BRIGHT, G.bright)
            apply_sg_theme()
            redraw(window)
            apply_menu(window)
        elif event == 'Edit Me':
            sg.execute_editor(__file__)
        elif event == 'Version':
            sg.popup_scrolled(__file__, f'{APP_NAME}  version {VERSION}', sg.get_versions(), keep_on_top=True, non_blocking=True, size=(70, 10))

    unregister_hotkeys()    # let go of the hotkeys first - a replacement copy may be waiting to register the same ones
    tray_stop()             # without it the icon "lingers" until moused over
    window.close()
    if instance_sock:
        instance_sock.close()

    sg.popup_auto_close(f'Exiting {APP_NAME}', '(This window auto-closes)')


def main():
    """ psghotkey: the card, the tray icon and the hotkeys.  A crash is shown in a window - a .pyw and the psghotkey command have no console """
    try:
        run()
    except Exception as e:
        sg.popup_error_with_traceback(f'{APP_NAME} crashed', e, traceback.format_exc())


def window_icon():
    return b'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'


if __name__ == '__main__':
    main()
