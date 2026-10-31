import PySimpleGUI as sg
import keyboard
import psgtray
import socket, threading, time
import os, shlex, sys
from typing import List, Any, Dict, ClassVar




r"""

      _____  _______  ______ _     _  _____  _______ _     _ _______ __   __
     |_____] |______ |  ____ |_____| |     |    |    |____/  |______   \_/  
     |       ______| |_____| |     | |_____|    |    |    \_ |______    |
     
     
    PySimpleHotkey
    
    A simple hotkey manager that runs in the system tray.
    
    Packages required:
        PySimpleGUI
        keyboard
        psgtray
    
    Define your hotkeys with the Settings window (tray menu or the Settings button).  They are stored in your own
    psghotkey.json user settings file, so every user has their own set.  At the moment, the actions are to insert text or launch a program.
    Nothing is defined until you add it.  Some examples of the kind of thing you can set up:
        ctrl+alt+p      Insert text      PySimpleGUI
        ctrl+alt+e      Insert text      your.name@example.com
        ctrl+alt+t      Insert text      Thanks for your help!
        ctrl+alt+n      Launch program   notepad.exe
        ctrl+alt+c      Launch program   calc.exe
    Hotkey names are the keyboard package's:  modifiers + key joined with "+", e.g.  ctrl+alt+h   alt+f9   ctrl+shift+1
    You can also modify the tray icon menu.
        Add a menu item and code in the event loop to do whatever you want when item is selected.

    On Windows each hotkey is registered with Windows itself (RegisterHotKey), so Windows does the matching, the key combination is
    swallowed instead of reaching the program underneath, and there is no keyboard hook for Windows to silently drop after a sleep,
    lock or busy moment (the keyboard package's hook has that problem).  The keyboard package is used to type the text and to record
    a hotkey with the Rec button.  On other systems the hotkeys go through keyboard.add_hotkey().

    Copyright 2021-2026 PySimpleGUI
    Licensed as LGPL3.
"""



version = '6.1'
__version__ = version.split()[0]

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
"""




# The hotkeys come from the user settings file (psghotkey.json).  Edit them with the Settings window (tray menu or Settings button)
hotkey_dict = {}        # maps a hotkey string (e.g. 'ctrl+alt+p') to the callable that performs its action
hotkey_info = {}        # maps a hotkey string to its (action, value) - what the main window's table shows

SETTINGS_FILENAME = 'psghotkey.json'
ACTION_TEXT = 'Insert text'
ACTION_LAUNCH = 'Launch program'
ACTIONS = (ACTION_TEXT, ACTION_LAUNCH)

# Main window keys
K_TABLE = '-TABLE-'
K_TABLE_DBL = '+DBL'                 # bound suffix - double-click on the table
K_LOG = '-LOG-'
K_MAIN_STATUS = '-MAIN STATUS-'
K_HOTKEY_FIRED = '-HOTKEY FIRED-'    # event sent (from the keyboard thread) when a hotkey runs, value = the hotkey
COLOR_PRIMARY = 'white on #1565c0'
COLOR_FIRED = 'white on #1565c0'
COLOR_OK_TEXT = '#43a047'


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
    """ Returns the callable the keyboard package runs when the hotkey is pressed.  It does the action, then tells the main window so it can log it """
    def run():
        if action == ACTION_LAUNCH:
            launch_program(value)
        else:
            type_text(value)
        if G.main_window is not None:
            G.main_window.write_event_value(K_HOTKEY_FIRED, hotkey)
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


def log(text, colors=None):
    """ Timestamped line in the main window's log """
    sg.cprint(time.strftime('%H:%M:%S'), c='gray60', end='  ')
    sg.cprint(text, c=colors)


def refresh_main_window(window:sg.Window):
    """ Register the hotkeys, fill the table and the header from hotkey_info, report in the log """
    bad = register_hotkeys()
    window[K_TABLE].update(values=[[hotkey, action, value.replace('\n', '⏎')] for hotkey, (action, value) in hotkey_info.items()])
    active = len(hotkey_info) - len(bad)
    window[K_MAIN_STATUS].update(f'●  {active} hotkey{"s" if active != 1 else ""} active', text_color=COLOR_OK_TEXT if active else COLOR_DIRTY_TEXT)
    if hotkey_info:
        log(f'{active} hotkeys active  ({settings_filename()})', 'white on #2e7d32')
    else:
        log('No hotkeys defined yet - click Settings to add some', 'black on #ffc107')
    for hotkey in bad:
        log(f'Could not register "{hotkey}" - bad key name, or another program already uses it', 'white on #b71c1c')


#  ███████╗███████╗████████╗████████╗██╗███╗   ██╗ ██████╗ ███████╗    ██╗    ██╗██╗███╗   ██╗██████╗  ██████╗ ██╗    ██╗
#  ██╔════╝██╔════╝╚══██╔══╝╚══██╔══╝██║████╗  ██║██╔════╝ ██╔════╝    ██║    ██║██║████╗  ██║██╔══██╗██╔═══██╗██║    ██║
#  ███████╗█████╗     ██║      ██║   ██║██╔██╗ ██║██║  ███╗███████╗    ██║ █╗ ██║██║██╔██╗ ██║██║  ██║██║   ██║██║ █╗ ██║
#  ╚════██║██╔══╝     ██║      ██║   ██║██║╚██╗██║██║   ██║╚════██║    ██║███╗██║██║██║╚██╗██║██║  ██║██║   ██║██║███╗██║
#  ███████║███████╗   ██║      ██║   ██║██║ ╚████║╚██████╔╝███████║    ╚███╔███╔╝██║██║ ╚████║██████╔╝╚██████╔╝╚███╔███╔╝
#  ╚══════╝╚══════╝   ╚═╝      ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝     ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝  ╚══╝╚══╝
#
#   A scrollable list of "blocks", one per hotkey, with Add / Delete / Clear / Save / Load / Move Up / Move Down.
#   (Same design as the MiniLauncher setup window.)  A block has 3 things:
#       Hotkey      e.g. ctrl+alt+p   (type it, or click Rec and press the key combination)
#       Action      Insert text  or  Launch program
#       Value       the text to type, or the path / command line to launch
#   Keyboard shortcuts:  Up/Down = move checked blocks     PgUp/PgDn = scroll a page     Home/End = top/bottom     Escape = close

SCROLLABLE_COLUMN_SIZE = (None, 600)
FRAME_BORDER_COLOR_NOT_SELECTED = 'gray30'
FRAME_BORDER_COLOR_SELECTED = 'chartreuse'
PLACEHOLDER_COLOR = 'steel blue'
HOTKEY_INPUT_LENGTH = 28
VALUE_INPUT_LENGTH = 80


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
    dirty = False                                       # True while the settings window has unsaved changes
    main_window : sg.Window = None                      # so hotkey callbacks (hotkey thread) can send events to the main window
    win_hotkeys : 'WindowsHotkeys' = None               # the RegisterHotKey thread (Windows only), created on first use


# Saved in the settings file (one set per hotkey, numbered)
K_HOTKEY = '-HOTKEY-'
KT_HOTKEY = lambda num: (K_HOTKEY, num)
K_ACTION = '-ACTION-'
KT_ACTION = lambda num: (K_ACTION, num)
K_VALUE = '-VALUE-'
KT_VALUE = lambda num: (K_VALUE, num)

# Settings window only
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
K_MOVE_UP = '-MOVE UP-'
K_MOVE_DOWN = '-MOVE DOWN-'
K_PAGE_UP = '-PAGE UP-'
K_PAGE_DOWN = '-PAGE DOWN-'
K_HOME = '-HOME-'
K_END = '-END-'
K_ESCAPE = '-ESCAPE-'
K_OK = '-OK-'
K_APPLY = '-APPLY-'
K_CANCEL = '-CANCEL-'
K_SEL_ALL = '-SELECT ALL-'
K_SEL_NONE = '-SELECT NONE-'
K_STATUS = '-STATUS-'

# Toolbar colours - green = safe/save, gold = unsaved changes, red = destructive
COLOR_SAVE = 'white on #2e7d32'
COLOR_SAVE_DIRTY = 'black on #ffc107'
COLOR_DANGER = 'white on #b71c1c'
COLOR_DIRTY_TEXT = '#ffc107'


# ------------------------------------------------------------ Settings file load / save ------------------------------------------------------------

def get_settings() -> sg.UserSettings:
    if G.hotkey_settings is None:
        G.hotkey_settings = sg.UserSettings(SETTINGS_FILENAME)
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
    """ Write a list of (hotkey, action, value) tuples to the settings file, replacing what was there """
    settings = get_settings()
    settings.write_new_dictionary({})
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
    sg.popup_quick_message(f'Saved {len(hotkeys)} hotkeys', font='_ 20', text_color='white', background_color='dark green')


# ------------------------------------------------------------ Blocks (one per hotkey) ------------------------------------------------------------

def make_a_block() -> sg.Frame:
    block_num = G.block_number
    Block.active_blocks[G.block_number] = Block(block_num=G.block_number, hotkey='', action=ACTION_TEXT, value='')
    G.block_number += 1

    block_layout = [[sg.Checkbox('', k=KT_CBOX(block_num), enable_events=True, p=0),
                     sg.Input(k=KT_HOTKEY(block_num), enable_events=True, placeholder='Hotkey  e.g. ctrl+alt+p', placeholder_justification='c', placeholder_background_color=PLACEHOLDER_COLOR, font='_ 12 bold', s=HOTKEY_INPUT_LENGTH, p=(2, 2), tooltip='Modifiers + key, e.g.  ctrl+alt+h   ctrl+shift+1   alt+f9\nor click Rec and press the keys'),
                     sg.B('Rec', k=KT_RECORD(block_num), tooltip='Click, then press the key combination you want', p=(2, 2)),
                     sg.Combo(ACTIONS, default_value=ACTION_TEXT, k=KT_ACTION(block_num), readonly=True, enable_events=True, s=(15, 1), p=(6, 2)),
                     sg.Push(),
                     sg.B(image_source=trash_icon, mouseover_image_source=trash_icon_red, button_color=f'red on {sg.theme_background_color()}', border_width=0, k=KT_DEL(block_num), tooltip='Delete this hotkey')],
                    [sg.Input(k=KT_VALUE(block_num), enable_events=True, placeholder='Text to insert   -or-   path / command to launch', placeholder_justification='c', placeholder_background_color=PLACEHOLDER_COLOR, s=VALUE_INPUT_LENGTH, p=(2, (0, 4)))],
                    ]

    block = sg.Frame('', [[sg.Column(block_layout, k=KT_COLUMN(block_num), expand_x=True, pad=0)]], k=KT_BLOCK(block_num), border_width_no_relief=3, border_color=FRAME_BORDER_COLOR_NOT_SELECTED, expand_x=True, p=0)
    return block


def add_block(window):
    window.extend_layout(window[K_ALL_COLS], [[make_a_block()]])
    window.refresh()
    window[K_ALL_COLS].contents_changed()
    window.refresh()
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


# ------------------------------------------------------------ Mini window (no titlebar, drawn border) ------------------------------------------------------------

# noinspection PyPep8Naming
def MiniWindow(title: str, layout: List, close_key: Any = 'Exit', **kwargs: Any) -> sg.Window:
    """ Returns a Window with no titlebar wrapped in a border with a fake titlebar and close button (the X sends close_key) """
    layout = wrap_in_border(title, layout, close_key)
    return sg.Window(title, layout, no_titlebar=True, grab_anywhere=True, keep_on_top=True, finalize=True, margins=(0, 0), **kwargs)


def wrap_in_border(title: str, layout_rows: list, close_key: Any = 'Exit') -> list:
    """
        ┌──────────────────────────┐
        │ ▌  Title              ✕  │
        ├──────────────────────────┤
        │   ...layout_rows...      │
        └──────────────────────────┘
    """
    titlebar = [sg.Text("▌", text_color=sg.theme_button_color_background(), font=("Segoe UI", 14)),
                sg.Text(title, font=("Segoe UI", 14, "bold"), expand_x=True),
                sg.Button(sg.SYMBOL_X_SMALL, key=close_key, border_width=0, pad=(2, 0), font=("Segoe UI", 11, "bold"), mouseover_colors=("#ffffff", "#a13544"), tooltip="Close")]

    layout = [[sg.Column([titlebar], expand_x=True, pad=0)],
              [sg.HorizontalSeparator(color=sg.theme_text_color(), pad=0)],
              *layout_rows]
    try:
        new_layout = [[sg.Frame("", layout, border_width_no_relief=2, p=0, expand_x=True, expand_y=True)]]      # Requires PySimpleGUI >= 6.2
    except TypeError:
        new_layout = [[sg.Frame("", layout, p=0, expand_x=True, expand_y=True)]]
    return new_layout


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


# ------------------------------------------------------------ The settings window ------------------------------------------------------------

def check_all_blocks(window:sg.Window, checked):
    for key in Block.active_blocks:
        window[KT_CBOX(key)].update(checked)
        window[KT_BLOCK(key)].update(border_color=FRAME_BORDER_COLOR_SELECTED if checked else FRAME_BORDER_COLOR_NOT_SELECTED)


def num_checked_blocks(window:sg.Window):
    return sum(1 for key in Block.active_blocks if window[KT_CBOX(key)].get())


def update_status(window:sg.Window):
    """ Refresh the status bar and the Save button colour (gold = unsaved changes) """
    num = len(Block.active_blocks)
    state = 'UNSAVED CHANGES' if G.dirty else 'saved'
    window[K_STATUS].update(f'{num} hotkey{"s" if num != 1 else ""}   ·   {num_checked_blocks(window)} checked   ·   {state}', text_color=COLOR_DIRTY_TEXT if G.dirty else sg.theme_text_color())
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
    """ Save the list, then make the hotkeys live and refresh the main window's table """
    save_blocks(window)
    G.dirty = False
    build_hotkey_dict()
    if G.main_window is not None:
        refresh_main_window(G.main_window)
    else:
        register_hotkeys()


def settings_window(location=(None, None), anchor=None):
    """ The hotkey settings window.  Returns when the window is closed.  Call build_hotkey_dict() afterwards to pick up the changes. """
    Block.active_blocks = {}
    col_layouts = [[]]
    col_layouts += [[make_a_block()]]       # add a dummy block so that the column width is set correctly

    #  Toolbar - grouped left to right:  list editing | ordering | selection ......... file
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
    all_columns = sg.Column(col_layouts, size=SCROLLABLE_COLUMN_SIZE, k=K_ALL_COLS, vertical_scroll_only=True, scrollable=True, expand_y=True, expand_x=True)
    status_bar = [sg.T('', k=K_STATUS, font='_ 10'), sg.Push(), sg.T(settings_filename(), font='_ 9', text_color='gray60', tooltip='The settings file the hotkeys are saved in')]
    layout = [[sg.Column([toolbar], expand_x=True, p=(4, (6, 2)))],
              [sg.Frame('Hotkey List', [[all_columns]], key='-FRAME-', expand_y=True, expand_x=True)],
              [sg.Column([status_bar], expand_x=True, p=(4, (2, 4)))]]

    window = MiniWindow('PySimpleHotkey Settings', layout, resizable=True, use_min_size=True, location=location, location_anchor=anchor, right_click_menu=sg.MENU_RIGHT_CLICK_EDITME_VER_EXIT, icon=window_icon())         # titlebar X sends 'Exit', handled like Cancel

    del col_layouts
    load_blocks(window)

    window.bind('<Prior>', K_PAGE_UP)
    window.bind('<Next>', K_PAGE_DOWN)
    window.bind('<Home>', K_HOME)
    window.bind('<End>', K_END)
    window.bind('<Escape>', K_CANCEL)
    window.bind('<Return>', K_OK)
    window.bind('<Control-s>', K_OK)
    scroll_canvas = window[K_ALL_COLS].widget.canvas
    recording_block = None
    G.dirty = False
    update_status(window)

    while True:
        event, values = window.read()
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
            sg.popup_scrolled(__file__, sg.get_versions(), keep_on_top=True, non_blocking=True, size=(70, 10))
        elif event == 'Edit Me':
            sg.execute_editor(__file__)
        elif event == 'Add':
            add_block(window)
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
                window[KT_BLOCK(block_num)].update(border_color=FRAME_BORDER_COLOR_SELECTED if window[KT_CBOX(block_num)].get() else FRAME_BORDER_COLOR_NOT_SELECTED)
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
                    sg.popup_quick_message('Nothing captured - type the hotkey instead', font='_ 14', text_color='white', background_color='#b71c1c')
                hotkey = values[event] or Block.active_blocks[block_num].hotkey
                Block.active_blocks[block_num].hotkey = hotkey
                if KT_RECORD(block_num) in window.key_dict:
                    window[KT_RECORD(block_num)].update('Rec', button_color=sg.theme_button_color())
                    window[KT_HOTKEY(block_num)].update(hotkey)
                G.dirty = True
        update_status(window)
    window.close()


# Settings window images - 25 x 25
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

# Hotkeys are registered with keyboard.add_hotkey() - see register_hotkeys() in the hotkey section near the top of the file.


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
K_QUIT_REQUEST = '-QUIT-REQUEST-'    # event sent to the window when a newer copy wants us to exit


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


def main():
    instance_sock, replaced_running_copy = claim_single_instance(INSTANCE_PORT)       # a previous copy, if any, is told to exit before we start
    build_hotkey_dict()

    menu = ['', ['Show Window', 'Hide Window', 'Settings', 'Edit Me', '---',  'Change Icon', ['Happy', 'Sad', 'Plain'], 'Exit']]

    header = [sg.Image(window_icon(), p=((0, 8), 0)), sg.T('PySimpleHotkey', font='_ 20'), sg.T(f'v{version}', font='_ 10', text_color='gray60', p=(0, (12, 0))), sg.Push(), sg.T('', k=K_MAIN_STATUS, font='_ 12 bold')]
    table = sg.Table(values=[], headings=['Hotkey', 'Action', 'Value'], col_widths=[20, 16, 50], auto_size_columns=False, justification='left', num_rows=8, k=K_TABLE, expand_x=True, expand_y=True, tooltip='Double-click a row to open Settings')
    toolbar = [sg.B('Settings', k='Settings', button_color=COLOR_PRIMARY, tooltip='Add, change or remove hotkeys'),
               sg.B('Hide to tray', k='Hide Window', tooltip='Keep running in the system tray   (Escape)'),
               sg.Push(),
               sg.B('Edit Me', tooltip='Open this program in your editor'),
               sg.B('Versions', tooltip='Python / PySimpleGUI / tkinter versions'),
               sg.B('Exit', button_color=COLOR_DANGER, tooltip='Stop PySimpleHotkey - the hotkeys stop working')]
    layout = [header,
              [sg.T('Hotkeys', font='_ 10 bold'), sg.Push(), sg.T(settings_filename(), font='_ 9', text_color='gray60', tooltip='Where the hotkeys are saved')],
              [table],
              [sg.T('Log', font='_ 10 bold')],
              [sg.Multiline(size=(96, 6), reroute_cprint=True, write_only=True, autoscroll=True, k=K_LOG, font='Courier 9', expand_x=True)],
              [sg.Column([toolbar], expand_x=True, p=0)],
              [sg.T('Closing this window hides it to the tray.  Double-click the tray icon, or right-click it and choose Show Window, to get it back.', font='_ 9', text_color='gray60')]]

    window = sg.Window('PySimpleHotkey', layout, finalize=True, enable_close_attempted_event=True, right_click_menu=menu, icon=window_icon(), resizable=True)
    G.main_window = window
    window[K_TABLE].bind('<Double-Button-1>', K_TABLE_DBL)
    window.bind('<Escape>', 'Hide Window')

    tray = psgtray.SystemTray(menu, single_click_events=False, window=window, icon=window_icon())
    tray.show_message('PySimpleHotkey', 'Running in the tray.  Double-click the icon for the window and settings.')
    if instance_sock:
        threading.Thread(target=instance_listener, args=(instance_sock, window, K_QUIT_REQUEST), daemon=True).start()

    if replaced_running_copy:                                   # the copy we replaced may hold the hotkeys for a few more seconds while it exits
        for _ in range(12):
            if not register_hotkeys():
                break
            time.sleep(0.5)
    refresh_main_window(window)
    window.hide()                                               # lives in the tray - the window is only shown when asked for

    while True:
        event, values = window.read()

        # IMPORTANT step. It's not required, but convenient. Set event to value from tray
        # if it's a tray event, change the event variable to be whatever the tray sent
        if event == tray.key:
            event = values[event]       # use the System Tray's event as if was from the window

        if event in (sg.WIN_CLOSED, 'Exit', K_QUIT_REQUEST):
            break

        if event in ('Show Window', sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            window.un_hide()
            window.bring_to_front()
        elif event in ('Hide Window', sg.WIN_CLOSE_ATTEMPTED_EVENT):
            window.hide()
            tray.show_icon()        # if hiding window, better make sure the icon is visible
            tray.show_message('Minimized to Tray', 'PySimpleHotkey minimized to system tray\nDouble Click to Restore')
        elif event == 'Happy':
            tray.change_icon(sg.EMOJI_BASE64_HAPPY_JOY)
        elif event == 'Sad':
            tray.change_icon(sg.EMOJI_BASE64_FRUSTRATED)
        elif event == 'Plain':
            tray.change_icon(sg.DEFAULT_BASE64_ICON)
        elif event in ('Settings', K_TABLE + K_TABLE_DBL):
            log('Settings opened')
            settings_window()                                      # returns when the settings window is closed. OK / Apply refresh this window
        elif event == K_HOTKEY_FIRED:
            hotkey = values[event]
            action, value = hotkey_info.get(hotkey, ('?', '?'))
            log(f'{hotkey}  →  {action}: {value}'.replace('\n', '⏎'), COLOR_FIRED)
            hotkeys = list(hotkey_info)
            if hotkey in hotkeys:
                window[K_TABLE].update(select_rows=[hotkeys.index(hotkey)])
        elif event == 'Edit Me':
            sg.execute_editor(__file__)
        elif event == 'Versions':
            sg.popup_scrolled(__file__, sg.get_versions(), keep_on_top=True, non_blocking=True, size=(70, 10))

    unregister_hotkeys()    # let go of the hotkeys first - a replacement copy may be waiting to register the same ones
    tray.close()            # optional but without a close, the icon may "linger" until moused over
    window.close()
    if instance_sock:
        instance_sock.close()

    sg.popup_auto_close('Exiting PySimpleHotkey', '(This window auto-closes)')

def window_icon():
    return b'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'


if __name__ == '__main__':
    main()
