import copy
import os
import re
import traceback
from typing import Callable

from .display import *

__all__ = [
    'color_input', 'decorator_input', 'info_input', 'info2_input', 'success_input',
    'debug_input', 'warn_input', 'error_input', 'exception_input',
    'ask', 'input_str', 'input_strs', 'input_float', 'input_floats',
    'input_int', 'input_ints', 'input_file',
    'get_selection', 'conditional_get_selection', 'get_selection_from_table'
]

##########################################################
# Simple Input
##########################################################
def color_input(text: str) -> str:
    """Applies style to `text` and calls input()."""

    text += '[0]'
    text = apply_style(text)
    return input(text)

def decorator_input(decorator: str, text: str, 
                    end_text: str = '[0] [darkgray][Enter][0]') -> str:
    """Prepends `decorator` and appends `end_text` to `text`, 
    then calls `color_input` and returns it.
    """

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

def exception_input(exception: Exception, block: bool = True) -> int:
    """Prints the exception args and the method, file & line where
    it was raised.

    If `block` is True (default), uses `error_input()` instead of `error()`.

    Returns the number of printed lines.
    """
    print()
    printed_lines = 1

    tb = traceback.extract_tb(exception.__traceback__)[-1]
    args = exception.args
    msg = exception.__class__.__name__
    details = tb.line
    if len(exception.args) == 1:
        args = exception.args[0]

    if isinstance(args, tuple):
        if len(args) == 0:
            if not isinstance(exception, AssertionError):
                details = ''
        elif isinstance(args[0], str):
            msg = args[0]
            details = ','.join(repr(arg) for arg in args[1:])
        else:
            details = ','.join(repr(arg) for arg in args)
    elif isinstance(args, str):
        if len(args) > 0:
            msg = args
            details = ''
    else:
        details = repr(args)

    if len(details) > 0:
        if len(details) <= 60:
            msg += f': [darkgray]{details}'
        else:
            debug(repr(details))
            printed_lines += 1

    filename = os.path.basename(tb.filename)
    msg = f'Abort[darkgray]({tb.name}@{filename}:{tb.lineno})[red]: {msg}'
    if block:
        error_input(msg)
    else:
        error(msg)

    printed_lines += 1
    return printed_lines

##########################################################
# Advanced Input
##########################################################
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

def input_str(msg: str, fallback = None,
              min_len: int|None = None, max_len: int|None = None) -> str:
    """Asks the user to input a string. Returns it.

    If `fallback` isn't `None`, it will be returned as-is if the user doesn't input anything.\n
    If `min_len` isn't `None`, the user won't be allowed to input a shorter string.\n
    If `max_len` isn't `None`, the user won't be allowed to input a longer string.
    """
    msg += ': '
    print()
    while 1:
        clear_last_line()
        # Print fallback value
        if fallback is not None and fallback is not Ellipsis:
            color_print((' ' * len(msg)) + f'[darkgray]{fallback}', end='\r')

        value = color_input(msg)
        # If fallback value is larger than the input, the gray
        # text will still be there so print the whole line again
        clear_last_line()
        if len(value) == 0 and fallback is not None:
            color_print(f'{msg}{fallback}')
        else:
            color_print(f'{msg}{value}')

        if len(value) == 0:
            if fallback is not None:
                return fallback
            continue
        if min_len is not None and len(value) < min_len:
            info_input(f'Input must have more than {min_len} chars')
            clear_last_line()
            continue
        if max_len is not None and len(value) > max_len:
            info_input(f'Input must have less than {max_len} chars')
            clear_last_line()
            continue

        return value

def input_strs(msg: str, fallback = None, min_len: int|None = None,
               max_len: int|None = None) -> list[str]:
    """Asks the user to input one or more strings (comma separated). Returns them.

    If `fallback` isn't `None`, it will be returned as-is if the user doesn't input anything.\n
    If `min_len` isn't `None`, all of the values will have at least that length.\n
    If `max_len` isn't `None`, all of the values will have at most that length.
    """
    msg += ': '
    print()
    while 1:
        clear_last_line()
        # Print fallback value
        if fallback is not None and fallback is not Ellipsis:
            fallback_str = str(fallback)
            if isinstance(fallback, list):
                fallback_str = ','.join(fallback)
            color_print((' ' * len(msg)) + f'[darkgray]{fallback_str}', end='\r')

        value = color_input(msg)
        # If fallback value is larger than the input, the gray
        # text will still be there so print the whole line again
        clear_last_line()
        if len(value) == 0 and fallback is not None and fallback is not Ellipsis:
            color_print(f'{msg}{fallback_str}')
        else:
            color_print(f'{msg}{value}')

        if len(value) == 0:
            if fallback is not None:
                return fallback
            continue

        values = value.split(',')
        for v in values:
            if min_len is not None and len(v) < min_len:
                info_input(f'All values must have more than {min_len} chars')
                clear_last_line()
                values = None
                break
            if max_len is not None and len(v) > max_len:
                info_input(f'All values must have less than {max_len} chars')
                clear_last_line()
                values = None
                break

        if values is None:
            continue

        return values

def _input_number(type: type, msg: str, fallback = None,
                  min = None, max = None, accepted_values: list = None):
    print()
    while 1:
        clear_last_line()
        value = input_str(msg, fallback)
        if value == fallback:
            # Return fallback as-is. Don't apply checks to it.
            return fallback

        try:
            result = type(value)
        except ValueError:
            continue

        if min is not None and result < min:
            info_input(f'Number can\'t be less than {min}')
            clear_last_line()
            continue
        if max is not None and result > max:
            info_input(f'Number can\'t be higher than {max}')
            clear_last_line()
            continue
        if accepted_values is not None and not result in accepted_values:
            info_input(f'Number must be one of the following: {accepted_values}')
            clear_last_line()
            continue

        return result
    
def _input_numbers(type: type, msg: str, fallback = None,
                   min = None, max = None, accepted_values = None) -> list:
    print()
    while 1:
        clear_last_line()
        values = input_strs(msg, fallback)
        if values == fallback:
            # Return fallback as-is. Don't apply checks to it.
            return fallback

        for i, value in enumerate(values):
            try:
                result = type(value)
            except ValueError:
                values = None
                break

            if min is not None and result < min:
                info_input(f'Numbers can\'t be less than {min}')
                clear_last_line()
                values = None
                break
            if max is not None and result > max:
                info_input(f'Numbers can\'t be higher than {max}')
                clear_last_line()
                values = None
                break
            if accepted_values is not None and not result in accepted_values:
                info_input(f'All numbers must be one of the following: {accepted_values}')
                clear_last_line()
                values = None
                break

            values[i] = result

        if values is None:
            continue

        return values
    
def input_float(msg: str, fallback = None,
                min: float|None = None, max: float|None = None,
                accepted_values: list[float]|None = None) -> float:
    """Asks the user to input a float. Returns it.
    
    If `fallback` isn't `None`, it will be returned as-is if the user doesn't input anything.\n
    If `min` isn't `None`, the user won't be allowed to input a lower number.\n
    If `max` isn't `None`, the user won't be allowed to input a higher number.\n
    If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    return _input_number(float, msg, fallback, min, max, accepted_values)

def input_floats(msg: str, fallback = None,
                 min: float|None = None, max: float|None = None,
                 accepted_values: list[float]|None = None) -> list[float]:
    """Asks the user to input one or more floats. Returns them.
    
    If `fallback` isn't `None`, it will be returned as-is if the user doesn't input anything.\n
    If `min` isn't `None`, the user won't be allowed to input a lower number.\n
    If `max` isn't `None`, the user won't be allowed to input a higher number.\n
    If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    return _input_numbers(float, msg, fallback, min, max, accepted_values)

def input_int(msg: str, fallback = None, 
              min: int|None = None, max: int|None = None,
              accepted_values: list[int]|None = None) -> int:
    """Asks the user to input an integer. Returns it.

    If `fallback` isn't `None`, it will be returned as-is if the user doesn't input anything.\n
    If `min` isn't `None`, the user won't be allowed to input a lower number.\n
    If `max` isn't `None`, the user won't be allowed to input a higher number.\n
    If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    return _input_number(int, msg, fallback, min, max, accepted_values)

def input_ints(msg: str, fallback = None,
               min: int|None = None, max: int|None = None,
               accepted_values: list[int]|None = None) -> list[int]:
    """Asks the user to input one or more ints. Returns them.
    
    If `fallback` isn't `None`, it will be returned as-is if the user doesn't input anything.\n
    If `min` isn't `None`, the user won't be allowed to input a lower number.\n
    If `max` isn't `None`, the user won't be allowed to input a higher number.\n
    If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    return _input_numbers(int, msg, fallback, min, max, accepted_values)

def input_file(msg: str, fallback: str|None = ...) -> str:
    """Asks the user to input a valid path of a file. Returns it.
    
    If `fallback` is a string, it'll be returned when the user
    doesn't input anything AND `fallback` is a valid file path.

    If `fallback` is `None`, `None` will be returned when the user
    doesn't input anything.
    """

    while 1:
        file = input_str(msg, fallback)
        if file is None:
            return None

        if file is not Ellipsis:
            # Strip quotes, this is useful because on Windows the
            # file explorer has an option to copy the path of a
            # folder/file, and it adds quotes to it
            file = file.strip('"')
            if os.path.isfile(file):
                break

        clear_last_line()

    return file

##########################################################
# Selections
##########################################################
def get_selection(*options, input_msg: str = 'Please select an option',
                  commands: dict[re.Pattern, Callable[[re.Match], None]] = {},
                  print_func: Callable[[str], None] = color_print,
                  invert_print_order: bool = False,
                  return_index: bool = False) -> str:
    """Shows the user a list with all the given options.
       Asks them to select one and returns it.

       If `return_index` is `True`, the index of the selected option
       will be returned instead of the option itself.
       
       If `commands` is supplied, all of its patterns will be tested against the user
       input and, if one of them matches, its function will be executed.
       
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

    if return_index:
        return selection - 1

    return options[selection - 1]

def conditional_get_selection(options: dict[str, bool],
                              input_msg = 'Please select an option',
                              commands: dict[re.Pattern, callable] = {},
                              print_func: callable = color_print,
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
                             commands: dict[re.Pattern, Callable[[re.Match], None]] = {},
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