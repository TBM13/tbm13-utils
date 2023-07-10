import copy
import os
import re

from .display import *
from .environment import IN_COLAB
__all__ = [
    'color_input', 'decorator_input', 'info_input', 'info2_input', 'success_input',
    'debug_input', 'warn_input', 'error_input', 'ask', 'input_float', 'input_int',
    'input_file', 'get_selection', 'conditional_get_selection', 'get_selection_from_table'
]

def color_input(text: str) -> str:
    """Applies style to `text` and calls input()."""

    # Colab doesn't properly display text printed 
    # by input() when it's too long
    if IN_COLAB:
        color_print(text)
        return input()

    text += '[0]'
    text = apply_style(text)
    return input(text)

def decorator_input(decorator: str, text: str, 
                    end_text: str = '[0] [darkgray][Enter][0]') -> str:
    """Adds `decorator` at the beggining of `text` and 
    `end_text` at the end, then calls input()."""

    text, decorator = move_new_lines(text, decorator)
    return color_input(decorator + text + end_text)

def info_input(text: str) -> str:
    return decorator_input(decorators['info'], text)
def info2_input(text: str) -> str:
    return decorator_input(decorators['info2'], text)
def success_input(text: str) -> str:
    return decorator_input(decorators['success'], text)
def debug_input(text: str) -> str:
    return decorator_input(decorators['debug'], text, '[0] [Enter][0]')
def warn_input(text: str) -> str:
    return decorator_input(decorators['warn'], text)
def error_input(text: str) -> str:
    return decorator_input(decorators['error'], text)

def ask(msg: str, yes_default: bool = False) -> bool:
    """Asks the user to input Yes or No (Y/N). Returns `True` if the answer is Yes.
    
    If `yes_default` is `True`, yes will be selected if the user doesn't input anything.
    """

    decorator = '[bold][blue][?][0]'
    msg2 = '[Y/n]' if yes_default else '[y/N]'
    msg2 = '[cyan]' + msg2

    msg, decorator = move_new_lines(msg, decorator)
    selection = color_input(f'{decorator} {msg} {msg2} ').upper()

    if len(selection) == 0:
        return yes_default
    if selection != 'Y' and selection != 'N':
        clear_last_line()
        return ask(msg, yes_default)

    return selection == 'Y'

def _input_number(type: type, msg: str, fallback = None,
                  min = None, max = None, accepted_values = None):
    print()
    while 1:
        clear_last_line()
        value = color_input(msg + ': ')
        if len(value) == 0:
            if fallback is not None:
                return fallback

            continue

        try:
            result = type(value)
        except ValueError:
            continue

        if min is not None and result < min:
            info_input(f"Number can't be less than {min}")
            clear_last_line()
            continue
        if max is not None and result > max:
            info_input(f"Number can't be higher than {max}")
            clear_last_line()
            continue
        if accepted_values is not None and not result in accepted_values:
            info_input(f"Invalid value {accepted_values}")
            clear_last_line()
            continue

        return result
    
def input_float(msg: str, fallback: float|None = None,
                min: float|None = None, max: float|None = None,
                accepted_values: list[float]|None = None) -> float:
    """Asks the user to input a float. Returns it.
    
    If `fallback` isn't `None`, it will be returned if the user doesn't input anything.\n
    If `min` isn't `None`, the user won't be allowed to input a lower number.\n
    If `max` isn't `None`, the user won't be allowed to input a higher number.\n
    If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    
    return _input_number(float, msg, fallback, min, max, accepted_values)

def input_int(msg: str, fallback: int|None = None, 
              min: int|None = None, max: int|None = None,
              accepted_values: list[int]|None = None) -> int:
    """Asks the user to input an integer. Returns it.

    If `fallback` isn't `None`, it will be returned if the user doesn't input anything.\n
    If `min` isn't `None`, the user won't be allowed to input a lower number.\n
    If `max` isn't `None`, the user won't be allowed to input a higher number.\n
    If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """

    return _input_number(int, msg, fallback, min, max, accepted_values)

def input_file(msg: str, fallback: str|None = None) -> str:
    """Asks the user to input a valid path of a file. Returns it.
    
    If `fallback` isn't `None` and user gives no input, returns `fallback`."""

    while 1:
        file = input(f'{msg}: ')
        # Strip quotes, this is useful because on Windows the
        # file explorer has an option to copy the path of a folder/file,
        # and it adds quotes to it
        file = file.strip('"')

        if fallback is not None and len(file) == 0:
            return fallback
        if os.path.isfile(file):
            break
        clear_last_line()

    return file

def get_selection(*options, input_msg: str = 'Please select an option',
                  commands: dict[re.Pattern, callable] = {},
                  print_func: callable = print,
                  invert_print_order: bool = False) -> str:
    """Shows the user a list with all the given options.
       Asks them to select one and returns it.
       
       If `commands` is supplied, all of its patterns will be tested against the user
       input, and if one of them matches, its function will be executed.
       
       `print_func` can be used to customize the list style by replacing the print
       function with a custom one.

       If `invert_print_order` is `True`, the options will be printed in reverse order.
    """

    if not invert_print_order:
        for i, option in enumerate(options):
            print_func(f'{i + 1}) {option}')
    else:
        for i, option in reversed(list(enumerate(options))):
            print_func(f'{i + 1}) {option}')

    print()
    while 1:
        selection_str = color_input(f'[darkgray]{input_msg}: ')

        # Detect commands and execute them
        for pattern, func in commands.items():
            match = re.match(pattern, selection_str)
            if match is not None:
                func(match)
                break

        try:
            selection = int(selection_str)
        except ValueError:
            clear_last_line()
            continue

        if selection > len(options) or selection < 1:
            clear_last_line()
            continue
            
        break

    return options[selection - 1]

def conditional_get_selection(options: dict[str, bool],
                              input_msg = 'Please select an option',
                              commands: dict[re.Pattern, callable] = {},
                              print_func: callable = print,
                              invert_print_order: bool = False) -> str:
    """Shows the user a list with the keys from `options` whose value are `True`. 
       Asks them to select one and returns it.
       
       If `commands` is supplied, all of its patterns will be tested against the user
       input, and if one of them matches, its function will be executed.

       `print_func` can be used to customize the list style by replacing the print
       function with a custom one.

       If `invert_print_order` is `True`, the options will be printed in reverse order.
    """

    options = [key for key, value in options.items() if value]
    return get_selection(*options, input_msg=input_msg, commands=commands, 
                         print_func=print_func, invert_print_order=invert_print_order)

def get_selection_from_table(columns: dict[str, int], options: list[list[str]],
                             input_msg: str = 'Please select an option',
                             commands: dict[re.Pattern, callable] = {},
                             invert_print_order: bool = False) -> int:
    """Just like `get_selection()`, but uses `print_table()` to print the options,
    and returns the index of the selected one."""

    columns = {'#': 4} | columns

    # We need to make a shallow copy of the options and
    # row lists so the option index is not added to the original one
    options = copy.copy(options)
    for i, row in enumerate(options):
        row = copy.copy(row)
        row.insert(0, f'{i + 1})')
        options[i] = row

    print_table(columns, options, invert_print_order=invert_print_order)
    selection = get_selection(*options, print_func=lambda *_: None,
                              input_msg=input_msg, commands=commands)

    for i, row in enumerate(options):
        if selection == row:
            return i

    raise Exception('Selection index not found')