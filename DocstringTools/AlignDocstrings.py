import PySimpleGUI as sg
import pyperclip
import sys

"""
    Read a .py file or the clipboard and line up the parms in the docstrings
"""

class STATES:
    START = 'start',
    READING_DOCSTRING = 'reading docstring',
    END_OF_DOCSTRING = 'end of doctring'

def read_the_file(filename):
    try:
        contents = open(filename, 'r', encoding='utf-8', errors='ignore').readlines()
    except Exception as error:
        sg.popup_error('Error reading the file', error)
        contents = None
    return contents

def process_docstring(docstring):
    # print('----------------------------------------')
    new_docstring = []
    max_len=0
    for line in docstring:
        first = line.index(':')
        second = line[first+1:].index(':')
        second_loc = first + second + 2
        max_len = max(max_len, second_loc)
        # print(line, end='')
    # have the max length, so now can shift everything based on that
    # print('========================================')
    for line in docstring:
        first = line.index(':')
        second = line[first+1:].index(':')
        second_loc = first + second + 2
        new_line = line[:second_loc]
        spaces = (max_len - second_loc) * ' '
        if line[second_loc:].lstrip():      # make sure there's something left after the strip or else will lose a newline
            new_line += spaces + ' ' + line[second_loc:].lstrip()
        else:
            new_line += spaces + ' ' + line[second_loc:]
        # print(new_line, end='')
        new_docstring.append(new_line)
    return new_docstring


def main(filename=None, use_clipboard=False):
    """

    :param filename:
    :param use_clipboard:
    :return:
    """
    doctring_items = (':param', ':type', ':return', ':rtype')

    if not use_clipboard and filename is None:
        filename = sg.popup_get_file('Filename to process', title='Docstring formatter', history=True, file_types=(('Python Files', '*.py'), ("ALL Files", "*.*"),))
        if not filename:
            sg.popup_error('No filename specified, cancelling', auto_close=True)
            exit()

    if not use_clipboard:
        contents = read_the_file(filename)
    else:
        contents = sg.clipboard_get()
        contents = contents.split('\n')
        contents = [line+'\n' for line in contents]

    state = STATES.START
    cur_docstring = []
    output = []
    for line in contents:
        if state == STATES.START:
            # if ':param' in line:
            if any([True for item in doctring_items if item in line]):
                state = STATES.READING_DOCSTRING
                cur_docstring = []
            else:
                output.append(line)

        if state == STATES.READING_DOCSTRING:
            if any([True for item in doctring_items if item in line]):
                cur_docstring.append(line)
            else:
                state = STATES.END_OF_DOCSTRING
                line_at_end_of_docstring = line

        if state == STATES.END_OF_DOCSTRING:
            new_docstring = process_docstring(cur_docstring)
            cur_docstring = []
            state = STATES.START
            new_docstring.append(line_at_end_of_docstring)
            output.extend(new_docstring)
            # output.append(line_at_end_of_docstring)

    # sg.popup_scrolled(output, title='New file', font='Courier 10')
    output = ''.join(output)
    pyperclip.copy(output)
    sg.popup_auto_close('Reformatting complete...', 'Your results are on the clipboard', '(This window autocloses)')


if __name__ == '__main__':
    if len(sys.argv) >1:
        if sys.argv[1] == '--clipboard':
            main(use_clipboard=True)
        else:
            main(filename=sys.argv[1])
    else:
        main()