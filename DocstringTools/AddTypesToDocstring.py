import PySimpleGUI as sg
import pyperclip
import sys

"""
    Read a .py file and line up the parms in the docstrings
"""

class STATES:
    START = 'start',
    READING_DOCSTRING = 'reading docstring',
    PROCESS_DOCSTRING = 'process docstring',
    END_OF_DOCSTRING = 'end of doctring'

doctring_parm_items = (':param', ':return')
doctring_type_items = (':type', ':rtype')
doctring_start_end_markers = ('"""', "'''")
docstring_line_pairs_dict = {':param':':type', ':return':':rtype'}


def process_docstring(docstring):
    """
    My docstring

    :param docstring:
    :return:
    """
    # print('----------------------------------------')
    new_docstring = []
    for line in docstring:
        if any([True for item in doctring_parm_items if item in line]):
            for item in docstring_line_pairs_dict.keys():
                if item in line:
                    new_docstring.append(line)
                    # find the location of the second :
                    first = line.index(':')
                    second = line[first+1:].index(':')
                    second_loc = first + second + 2
                    if second_loc-1 != first + len(item): # if there is a variable name after the item
                        variable = line[first + len(item)+1:second_loc-1]
                        # print(f'** VARIABLE = "{variable}"')
                        new_line = ' ' * first + docstring_line_pairs_dict[item] + ' ' + variable + ':'
                        # print(line)
                        # print(new_line)
                        new_docstring.append(new_line)
                    else:
                        new_line = ' ' * first + docstring_line_pairs_dict[item] + ':'
                        new_docstring.append(new_line)
        else:
            new_docstring.append(line)
    return new_docstring



def main():
    contents = sg.clipboard_get()
    contents = contents.split('\n')
    # contents = [line+'\n' for line in contents]

    state = STATES.START
    cur_docstring = []
    output = []
    process_performed = False
    for line in contents:
        if state == STATES.START:
            # Look for start of docstring
            if any([True for item in doctring_start_end_markers if item in line]):
                state = STATES.READING_DOCSTRING
                cur_docstring = []
                output.append(line)
                continue

        if state == STATES.READING_DOCSTRING:
            cur_docstring.append(line)
            # if an end marker
            if any([True for item in doctring_start_end_markers if item in line]):
                state = STATES.PROCESS_DOCSTRING
            elif any([True for item in doctring_type_items if item in line]):
                print('Found a type so aborting')
                state = STATES.START

        if state == STATES.PROCESS_DOCSTRING:
            new_docstring = process_docstring(cur_docstring)
            cur_docstring = []
            state = STATES.START
            output.extend(new_docstring)
            # output.append(line)
            process_performed = True

    if process_performed:
        output = '\n'.join(output)
        # sg.popup_scrolled(output)
        sg.popup_auto_close('Reformatting complete...', 'Your results are on the clipboard', '(This window autocloses)')
        pyperclip.copy(output)
    else:
        sg.popup_auto_close('NO docstring with missing types found', '(This window autocloses)')


if __name__ == '__main__':
    main()