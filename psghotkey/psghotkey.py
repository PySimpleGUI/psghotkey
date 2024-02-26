'''
Copyright 2021-2024 PySimpleSoft, Inc. and/or its licensors. All rights reserved.

Redistribution, modification, or any other use of PySimpleGUI or any portion thereof is subject
to the terms of the PySimpleGUI License Agreement available at https://eula.pysimplegui.com.

You may not redistribute, modify or otherwise use PySimpleGUI or its contents except pursuant
to the PySimpleGUI License Agreement.
'''

import os
import sys
import PySimpleGUI as sg
import keyboard
import psgtray

version = '5.0.0'
__version__ = version.split()[0]


"""
    PySimpleHotkey
    
    A simple hotkey manager that runs in the system tray.
    
    Packages required:
        PySimpleGUI
        keyboard
        psgtray
    
    Define your hotkeys in the dictionary.  At the moment, the actions are to insert text or launch a program.
    
    Improvement ideas:
        This program could be extended to store the settings in a User Settings file instead of in the code.
        The keyboard handler is hooking in a low level. 
            Callbacks into this code happen when shift, control, etc are pressed
            There are likely better ways that the keyboard package could be used
            Didn't take the time to dig further into optimizing    
"""

'''
M""M                     dP            dP dP                   
M  M                     88            88 88                   
M  M 88d888b. .d8888b. d8888P .d8888b. 88 88 .d8888b. 88d888b. 
M  M 88'  `88 Y8ooooo.   88   88'  `88 88 88 88ooood8 88'  `88 
M  M 88    88       88   88   88.  .88 88 88 88.  ... 88       
M  M dP    dP `88888P'   dP   `88888P8 dP dP `88888P' dP       
MMMM
'''


def pip_install_thread(window, sp):
    window.write_event_value('-THREAD-', (sp, 'Install thread started'))
    for line in sp.stdout:
        oline = line.decode().rstrip()
        window.write_event_value('-THREAD-', (sp, oline))



def pip_install_latest():

    pip_command = '-m pip install --upgrade --no-cache-dir PySimpleGUI>=5'

    python_command = sys.executable  # always use the currently running interpreter to perform the pip!
    if 'pythonw' in python_command:
        python_command = python_command.replace('pythonw', 'python')

    layout = [[sg.Text('Installing PySimpleGUI', font='_ 14')],
              [sg.Multiline(s=(90, 15), k='-MLINE-', reroute_cprint=True, reroute_stdout=True, echo_stdout_stderr=True, write_only=True, expand_x=True, expand_y=True)],
              [sg.Push(), sg.Button('Downloading...', k='-EXIT-'), sg.Sizegrip()]]

    window = sg.Window('Pip Install PySimpleGUI Utilities', layout, finalize=True, keep_on_top=True, modal=True, disable_close=True, resizable=True)

    window.disable_debugger()

    sg.cprint('Installing with the Python interpreter =', python_command, c='white on purple')

    sp = sg.execute_command_subprocess(python_command, pip_command, pipe_output=True, wait=False)

    window.start_thread(lambda: pip_install_thread(window, sp), end_key='-THREAD DONE-')

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or (event == '-EXIT-' and window['-EXIT-'].ButtonText == 'Done'):
            break
        elif event == '-THREAD DONE-':
            sg.cprint('\n')
            show_package_version('PySimpleGUI')
            sg.cprint('Done Installing PySimpleGUI.  Click Done and the program will restart.', c='white on red', font='default 12 italic')
            window['-EXIT-'].update(text='Done', button_color='white on red')
        elif event == '-THREAD-':
            sg.cprint(values['-THREAD-'][1])

    window.close()

def suggest_upgrade_gui():
    layout = [[sg.Image(sg.EMOJI_BASE64_HAPPY_GASP), sg.Text(f'PySimpleGUI 5+ Required', font='_ 15 bold')],
              [sg.Text(f'PySimpleGUI 5+ required for this program to function correctly.')],
              [sg.Text(f'You are running PySimpleGUI {sg.version}')],
              [sg.Text('Would you like to upgrade to the latest version of PySimpleGUI now?')],
              [sg.Push(), sg.Button('Upgrade', size=8, k='-UPGRADE-'), sg.Button('Cancel', size=8)]]

    window = sg.Window(title=f'Newer version of PySimpleGUI required', layout=layout, font='_ 12')

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, 'Cancel'):
            window.close()
            break
        elif event == '-UPGRADE-':
            window.close()
            pip_install_latest()
            sg.execute_command_subprocess(sys.executable, __file__, pipe_output=True, wait=False)
            break


def make_str_pre_38(package):
    return f"""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import pkg_resources
try:
    ver=pkg_resources.get_distribution("{package}").version.rstrip()
except:
    ver=' '
print(ver, end='')
"""

def make_str(package):
    return f"""
import importlib.metadata

try:
    ver = importlib.metadata.version("{package}")
except importlib.metadata.PackageNotFoundError:
    ver = ' '
print(ver, end='')
"""


def show_package_version(package):
    """
    Function that shows all versions of a package
    """
    interpreter = sg.execute_py_get_interpreter()
    sg.cprint(f'{package} upgraded to ', end='', c='red')
    # print(f'{interpreter}')
    if sys.version_info.major == 3 and sys.version_info.minor in (6, 7):  # if running Python version 3.6 or 3.7
        pstr = make_str_pre_38(package)
    else:
        pstr = make_str(package)
    temp_file = os.path.join(os.path.dirname(__file__), 'temp_py.py')
    with open(temp_file, 'w') as file:
        file.write(pstr)
    sg.execute_py_file(temp_file, interpreter_command=interpreter, pipe_output=True, wait=True)
    os.remove(temp_file)



def upgrade_check():
    if not sg.version.startswith('5'):
        suggest_upgrade_gui()
        exit()



'''
MM"""""""`YM          MP""""""`MM oo                     dP          M""MMMMM""MM            dP   dP                         
MM  mmmmm  M          M  mmmmm..M                        88          M  MMMMM  MM            88   88                         
M'        .M dP    dP M.      `YM dP 88d8b.d8b. 88d888b. 88 .d8888b. M         `M .d8888b. d8888P 88  .dP  .d8888b. dP    dP 
MM  MMMMMMMM 88    88 MMMMMMM.  M 88 88'`88'`88 88'  `88 88 88ooood8 M  MMMMM  MM 88'  `88   88   88888"   88ooood8 88    88 
MM  MMMMMMMM 88.  .88 M. .MMM'  M 88 88  88  88 88.  .88 88 88.  ... M  MMMMM  MM 88.  .88   88   88  `8b. 88.  ... 88.  .88 
MM  MMMMMMMM `8888P88 Mb.     .dM dP dP  dP  dP 88Y888P' dP `88888P' M  MMMMM  MM `88888P'   dP   dP   `YP `88888P' `8888P88 
MMMMMMMMMMMM      .88 MMMMMMMMMMM               88                   MMMMMMMMMMMM                                        .88 
              d8888P                            dP                                                                   d8888P
'''

# Defintions of the hotkeys
DOCSTRING_SHORTCUT = 'ctrl+alt+shift+d'
DOCSTRING_TYPES_SHORTCUT = 'ctrl+alt+shift+f5'
PYSIMPLEGUI_SHORTCUT = 'alt+shift+p'

# dictionary that maps a hotkey to an action
hotkey_dict = {
    DOCSTRING_SHORTCUT :        (lambda :  sg.execute_py_file(r'DocstringTools\AlignDocstrings.py', '--clipboard', cwd='.')),
    DOCSTRING_TYPES_SHORTCUT :  (lambda :  sg.execute_py_file(r'DocstringTools\AddTypesToDocstring.py', cwd='.')),
    PYSIMPLEGUI_SHORTCUT:       (lambda: keyboard.write('PySimpleGUI')),
    }


'''
M""MMMMM""M M#"""""""'M     dP                         dP       
M  MMMM' .M ##  mmmm. `M    88                         88       
M       .MM #'        .M    88d888b. .d8888b. .d8888b. 88  .dP  
M  MMMb. YM M#  MMMb.'YM    88'  `88 88'  `88 88'  `88 88888"   
M  MMMMb  M M#  MMMM'  M    88    88 88.  .88 88.  .88 88  `8b. 
M  MMMMM  M M#       .;M    dP    dP `88888P' `88888P' dP   `YP 
MMMMMMMMMMM M#########M
'''

def custom_hotkey(event):
    """ Hook and react to hotkeys with custom handler """
    try:
        pressed_keys = [e.name.lower() for e in keyboard._pressed_events.values()]
    except AttributeError:  # Fn might return as None
        pressed_keys = []

    for hotkey, func in hotkey_dict.items():
        pressed = all(key in pressed_keys for key in hotkey.split('+'))
        if pressed:
            # print('matched hotkey found', hotkey)
            func()


'''
M"""""`'"""`YM          oo          
M  mm.  mm.  M                      
M  MMM  MMM  M .d8888b. dP 88d888b. 
M  MMM  MMM  M 88'  `88 88 88'  `88 
M  MMM  MMM  M 88.  .88 88 88    88 
M  MMM  MMM  M `88888P8 dP dP    dP 
MMMMMMMMMMMMMM
'''

def main():

    sg.user_settings_filename(filename='psghotkey.json')
    upgrade_check()

    sg.theme('dark gray 13')

    keyboard.hook(custom_hotkey)

    menu = ['', ['Show Window', 'Hide Window', 'Edit Me', '---',  'Change Icon', ['Happy', 'Sad', 'Plain'], 'Exit']]

    layout = [[sg.T('PySimpleHotkey', font='_ 20')],
              [sg.T('Double clip icon to restore or right click and choose Show Window')],
              [sg.Multiline(size=(80,15), reroute_stdout=False, reroute_cprint=True, write_only=True, key='-OUT-')],
              [sg.B('Hide Window'), sg.B('Show Hotkeys'), sg.B('Edit Me'), sg.B('Versions'), sg.Button('Exit')]]

    window = sg.Window('PySimpleHotkey', layout, finalize=True, enable_close_attempted_event=True, right_click_menu=menu, icon=window_icon())

    tray = psgtray.SystemTray(menu, single_click_events=False, window=window, icon=window_icon())
    tray.show_message('PySimpleHotkey', 'PySimpleHotkey Started!')

    sg.cprint(f'Your hotkeys:', c='white on red')
    for key in hotkey_dict.keys():
        sg.cprint(key, c='white on green')

    while True:
        event, values = window.read()

        # IMPORTANT step. It's not required, but convenient. Set event to value from tray
        # if it's a tray event, change the event variable to be whatever the tray sent
        if event == tray.key:
            sg.cprint(f'System Tray Event = ', values[event], c='white on red')
            event = values[event]       # use the System Tray's event as if was from the window

        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        sg.cprint(event, values)

        if event in ('Show Window', sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            window.un_hide()
            window.bring_to_front()
        elif event in ('Hide Window', sg.WIN_CLOSE_ATTEMPTED_EVENT):
            window.hide()
            tray.show_icon()        # if hiding window, better make sure the icon is visible
            tray.show_message('Minimized to Tray', 'PySimpleHotkey minimized to system tray\nDouble Click to Restore')
            # tray.notify('System Tray Item Chosen', f'You chose {event}')
        elif event == 'Happy':
            tray.change_icon(sg.EMOJI_BASE64_HAPPY_JOY)
        elif event == 'Sad':
            tray.change_icon(sg.EMOJI_BASE64_FRUSTRATED)
        elif event == 'Plain':
            tray.change_icon(sg.DEFAULT_BASE64_ICON)
        elif event == 'Show Hotkeys':
            sg.cprint(f'Your hotkeys:', c='white on red')
            for key in hotkey_dict.keys():
                sg.cprint(key, c='white on green')
        elif event == 'Edit Me':
            sg.execute_editor(__file__)
        elif event == 'Versions':
            sg.cprint(sg.get_versions(), c='white on purple')

    tray.close()            # optional but without a close, the icon may "linger" until moused over
    window.close()

    sg.popup_auto_close('Exiting PySimpleHotkey', '(This window auto-closes)')

def window_icon():
    return b'iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAABmJLR0QA/wD/AP+gvaeTAAAFgklEQVRYCe1YXW8UVRh+Z+bMfra0F3jBhTf+CBN+CDdceWdi/ELUBAI1orWImiIaEhRBiUYSY2L8E0bvjUm7YEsp7bYo9Gu3O3POGZ7n7E53uh2UEN1CMnTPfDzn632f834NIsW/goGCgYKBgoGCgYKBgoHHZsD75dffWvMLi1Wb2F2LJHhLhFc8ZH85EIfljuW8gfF8Zet2pU986zUHuUsP4K2/etoTJJ4ceuZgSy01V6q/zzZEG8ORT01TgS8qVDWljRYD4dmeGukpKI7CxJEora0Ya8VaI2++9KJYKDM/Py/f/fSzVCpVDnVt4vjr7r56965MX/rS9Q0Dc5vicuK1l0XHsSwsLMjXP/wo9foIiNeijI4htIYC1g2o1WpSrVZla31DPPyFpRKmd39aayCy00f0/8bS/eMokhJkKZfLbn/lBxJFFicQa0mSxCkwB+brUODPuTnRUMzAvAKrKKesrKyI53ky24C/9PqGgaX73wLzFQjfuHFjRzZtYvG+uPJN8kfjJszISGd7W1pbW1BGS6lckfrIqPi+7xTI6yMrg+P/a+xh+48eGJfnnj2EEwCbNjEQ2gqPq+YJTgRHo7qmY+Ef1CCvbxjYw/b3ELtNbOgDsH9DJ7Yy8dYxCZWCc3QV4mS2Jszn4pVrUq5U5OzESeojq6ur8sH0Z0PDTr3xqoRhKPfu35fzl75yhHcMnDiGYyaIQBRUBYGzcwUlnJS9y9iBA7K1tSHOg4E5x4U/DBOjA9OcRup1CG8gSiI6YhiFIxjbdeL1jQ2pgmXmBDYqxfvS0pKk0Yqn4UP42dnZoWKUhQrwzgYexepIvMlzHyW3FpfFDJQSHBB1OtJutZzGYaksNWjPWLwf2NTpk0IT2tzclDMfTwtJPDg+SidGJoajDtZCVEDB5qoIqwmUC1RICOk7lP3AUtbTkA9bRziFE5NRxnuLXDB56oSUkSw4mI1Zd2r6AkJqWT6dmuQcWYHznp48OzTszIm3hfGfOYgMUi5aQAWmHkexqAgX2jk1oxMHcGQ2DqbDtLY2GVed8HReHt0wMQqfDSpUgPt7qIV0KeyakKUTw0zI+OgIawwDu7dy584dOCpNzEiz2XRJbWaGzjs8bAM2TyVIMluzudKVKdESI4d5rxw7nvy1ti40IbLOxmy6vd0WhlcVllAb1WBvWvYD83qVwKBMtWpdRiolJrLIfQvQhCg8mw8zYikBDSQIlFNuvzBkVYoke/e30mE5HSMdJy4KJXLu3QmUqUwUFuVENzfQdM6c+8SVGVcvfg4z8oS54PjJ0w6bnnpfaqheSQDtM71nn1Msvad9jUZDLn/7PYQTuXzh/K61UWzKh++c2iPPMkz5PcjDxKYjZuI4hpKweUQhlqrscCr3LmNjYy4XcHPf95wpBThWRgJiTHxZJ+tNe6Rbu93+x7Vz5UFVwL3BsEBjRCEcA52DwrA8psApQ7zfXlyE01DJUJaXmzApX2ZmZnawtbW1HZY4no1r8T7YBvE5lO3M8Mbkr83THx8fdwGFMnK9hdu33d4aczx8xntHjh5N2pGBQohLGd6YH5iJE1SqASpTFnIGddMglsbnzNR/fXyctfPmJLojisnAmv5Xf7o7nSYso6SGafmBcgrmYWQ1nfOo97x18rDs2nv64be60/MBjf+iyN8cHwco3Hh0/f48rN/76E956+Rh2RUz/SA2QjGnTBxb6yl/7xlkJz6Bz0i++Bq0KtpuX0tU6QXx8e0LBfGh8wRKu1skmla03ZL1e39fpcje84cPXy+F5SOsUbMngVPqz8y8ZMdkFebC/QnpE/IJ4wNbCmHSrleHA8GPj7z1t3NvhFGT4YfXKO4km2vr1+du3jja7SiuBQMFAwUDBQMFAwUD+8PAA1iNROeLU6xdAAAAAElFTkSuQmCC'


if __name__ == '__main__':
    main()
