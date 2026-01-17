import copy
import os
import re
import traceback
from datetime import date
from typing import Callable, overload

from . import display
from .display import *

__all__ = [
    'color_input', 'decorator_input', 'info_input', 'info2_input', 'success_input',
    'debug_input', 'warn_input', 'error_input', 'exception_input',
    'ask', 'input_str', 'input_strs', 'input_float', 'input_floats',
    'input_int', 'input_ints', 'input_file', 'input_date',
    'get_selection', 'get_selection_index', 'get_selection_from_table'
]

##########################################################
# Simple Input
##########################################################
def color_input(text: str) -> str:
    """Applies style to `text` and calls input()."""

    text = apply_style(text + '[0]')
    return input(text)

def decorator_input(decorator: str, text: str, 
                    end_text: str = '[0] [darkgray][Enter][0]') -> str:
    """Prepends `decorator` and appends `end_text` to `text`, 
    then calls `color_input` and returns it.
    """

    text, decorator = move_new_lines(text, decorator)
    return color_input(decorator + text + end_text)

def info_input(text: str) -> str:
    return decorator_input(display.INFO_DECORATOR, text)
def info2_input(text: str) -> str:
    return decorator_input(display.INFO2_DECORATOR, text)
def success_input(text: str) -> str:
    return decorator_input(display.SUCCESS_DECORATOR, text)
def debug_input(text: str) -> str:
    return decorator_input(display.DEBUG_DECORATOR, text, '[0] [Enter][0]')
def warn_input(text: str) -> str:
    return decorator_input(display.WARN_DECORATOR, text)
def error_input(text: str) -> str:
    return decorator_input(display.ERROR_DECORATOR, text)

def exception_input(exception: Exception, block: bool = True) -> int:
    """Prints the exception args and the method, file & line where
    it was raised.

    If `block` is True (default), blocks using `error_input`.

    Returns the number of printed lines.
    """
    print()
    printed_lines = 1

    tb = traceback.extract_tb(exception.__traceback__)[-1]
    args = exception.args
    msg = exception.__class__.__name__
    details = tb.line or ''
    if len(exception.args) == 1:
        args = exception.args[0]

    if isinstance(args, tuple):
        if len(args) == 0:  # type: ignore
            if not isinstance(exception, AssertionError):
                details = ''
        elif isinstance(args[0], str):
            msg = args[0]
            details = ','.join(repr(arg) for arg in args[1:])   # type: ignore
        else:
            details = ','.join(repr(arg) for arg in args)       # type: ignore
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

@overload
def input_str(msg: str, *, min_len: int|None = None, max_len: int|None = None) -> str:
    """Asks the user to input a string and returns it.

    * If `min_len` isn't `None`, the user won't be allowed to input a shorter string.
    * If `max_len` isn't `None`, the user won't be allowed to input a longer string.
    """
    ...
@overload
def input_str[T](msg: str, fallback: T, min_len: int|None = None, max_len: int|None = None) -> str|T:
    """Asks the user to input a string and returns it.
    Returns `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * If `min_len` isn't `None`, the user won't be allowed to input a shorter string.
    * If `max_len` isn't `None`, the user won't be allowed to input a longer string.
    """
    ...
def input_str(msg: str, fallback: object = ..., 
              min_len: int|None = None, max_len: int|None = None) -> object:
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
        if len(value) == 0 and fallback is not Ellipsis:
            color_print(f'{msg}{fallback}')
        else:
            color_print(f'{msg}{value}')

        if len(value) == 0:
            if fallback is not Ellipsis:
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
    
    raise Exception()

@overload
def input_strs(msg: str, *, min_len: int|None = None, max_len: int|None = None) -> list[str]:
    """Asks the user to input one or more strings (comma separated). Returns them.

    * If `min_len` isn't `None`, all of the values will have at least that length.
    * If `max_len` isn't `None`, all of the values will have at most that length.
    """
    ...
@overload
def input_strs[T](msg: str, fallback: T, min_len: int|None = None, max_len: int|None = None) -> list[str]|T:
    """Asks the user to input one or more strings (comma separated).
    Returns them or `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * If `min_len` isn't `None`, the user won't be allowed to input a shorter string.
    * If `max_len` isn't `None`, the user won't be allowed to input a longer string.
    """
    ...
def input_strs(msg: str, fallback: object = ...,
               min_len: int|None = None, max_len: int|None = None) -> object:
    msg += ': '
    print()

    fallback_str = None
    if fallback is not None and fallback is not Ellipsis:
        fallback_str = str(fallback)            # type: ignore
        if isinstance(fallback, list):
            fallback_str = ','.join(str(x) for x in fallback) # type: ignore

    while 1:
        clear_last_line()
        # Print fallback value
        if fallback_str is not None:
            color_print((' ' * len(msg)) + f'[darkgray]{fallback_str}', end='\r')
        value = color_input(msg)

        # Print the whole line again so as to clear the fallback value
        clear_last_line()
        if len(value) == 0 and fallback_str is not None:
            color_print(msg + fallback_str)
        else:
            color_print(msg + value)

        if len(value) == 0:
            if fallback is not Ellipsis:
                return fallback     # type: ignore

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
    
    raise Exception()

def _input_number[T: int|float](
        type: type[T], msg: str, fallback: object = ...,
        min: T|None = None, max: T|None = None,
        accepted_values: list[T]|None = None
    ) -> T|object:
    print()
    while 1:
        clear_last_line()
        value = input_str(msg, fallback)
        if value == fallback:
            return fallback

        try:
            result = type(value)   # type: ignore
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
        if accepted_values is not None and result not in accepted_values:
            info_input(f'Number must be one of the following: {accepted_values}')
            clear_last_line()
            continue

        return result
    
    raise Exception()
    
def _input_numbers[T: int|float](
        type: type[T], msg: str, fallback: object = ...,
        min: T|None = None, max: T|None = None,
        accepted_values: list[T]|None = None
    ) -> list[T]|object:
    print()
    while 1:
        clear_last_line()
        values = input_strs(msg, fallback)
        if values == fallback:
            return fallback

        for i, value in enumerate(values):  # type: ignore
            try:
                result = type(value)        # type: ignore
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

            values[i] = result      # type: ignore

        if values is None:
            continue

        return values

@overload
def input_int(msg: str, *, 
              min: int|None = None, max: int|None = None, 
              accepted_values: list[int]|None = None) -> int:
    """Asks the user to input an int. Returns it.

    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
@overload
def input_int[T](msg: str, fallback: T, 
                 min: int|None = None, max: int|None = None, 
                 accepted_values: list[int]|None = None) -> int|T:
    """Asks the user to input an int. Returns it.
    Returns `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
def input_int(msg: str, fallback: object = ...,
              min: int|None = None, max: int|None = None,
              accepted_values: list[int]|None = None) -> int|object:
    return _input_number(int, msg, fallback, min, max, accepted_values)

@overload
def input_float(msg: str, *, 
                min: float|None = None, max: float|None = None, 
                accepted_values: list[float]|None = None) -> float:
    """Asks the user to input a float. Returns it.

    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
@overload
def input_float[T](msg: str, fallback: T, 
                   min: float|None = None, max: float|None = None, 
                   accepted_values: list[float]|None = None) -> float|T:
    """Asks the user to input a float. Returns it.
    Returns `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
def input_float(msg: str, fallback: object = ...,
                min: float|None = None, max: float|None = None,
                accepted_values: list[float]|None = None) -> float|object:
    return _input_number(float, msg, fallback, min, max, accepted_values)

@overload
def input_ints(msg: str, *, 
               min: int|None = None, max: int|None = None, 
               accepted_values: list[int]|None = None) -> list[int]:
    """Asks the user to input one or more ints. Returns them.

    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
@overload
def input_ints[T](msg: str, fallback: T, 
                  min: int|None = None, max: int|None = None, 
                  accepted_values: list[int]|None = None) -> list[int]|T:
    """Asks the user to input one or more ints.
    Returns them or `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
def input_ints(msg: str, fallback: object = ...,
               min: int|None = None, max: int|None = None,
               accepted_values: list[int]|None = None) -> list[int]|object:
    return _input_numbers(int, msg, fallback, min, max, accepted_values)

@overload
def input_floats(msg: str, *, 
                 min: float|None = None, max: float|None = None, 
                 accepted_values: list[float]|None = None) -> list[float]:
    """Asks the user to input one or more floats. Returns them.

    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
@overload
def input_floats[T](msg: str, fallback: T, 
                    min: float|None = None, max: float|None = None, 
                    accepted_values: list[float]|None = None) -> list[float]|T:
    """Asks the user to input one or more floats.
    Returns them or `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * If `min` isn't `None`, the user won't be allowed to input a lower number.
    * If `max` isn't `None`, the user won't be allowed to input a higher number.
    * If `accepted_values` isn't `None`, the user won't be allowed to input any value not inside it.
    """
    ...
def input_floats(msg: str, fallback: object = ...,
                 min: float|None = None, max: float|None = None,
                 accepted_values: list[float]|None = None) -> list[float]|object:
    return _input_numbers(float, msg, fallback, min, max, accepted_values)

@overload
def input_file(msg: str) -> str:
    """Asks the user to input the valid path of a file. Returns it."""
    ...
@overload
def input_file[T](msg: str, fallback: T) -> str|T:
    """Asks the user to input the valid path of a file. Returns it.

    * `fallback` can't be `Ellipsis`. When the user doesn't input anything:
      * Returns it as-is if it's not a `str`.
      * If it's `str`, returns it ONLY if it's a valid file path.
    """
    ...
def input_file(msg: str, fallback: str|object = ...) -> str|object:
    file = input_str(msg, fallback)
    if not isinstance(file, str):
        return fallback

    # Strip quotes, since the Windows explorer copies paths with them
    file = file.strip('"')
    if os.path.isfile(file):
        return file

    clear_last_line()
    return input_file(msg, fallback)

@overload
def input_date(msg: str) -> date:
    """Asks the user to input a date. Returns it.
    
    Valid formats:
    * `YYYY-MM-DD` or `YYYY/MM/DD`
    * `DD-MM-YYYY` or `DD/MM/YYYY`
    * Zeros in day and month are optional (e.g. `2024-6-5` or `5/6/2024`)
    """
    ...
@overload
def input_date[T](msg: str, fallback: T) -> date|T:
    """Asks the user to input a date. Returns it.
    Returns `fallback` if the user doesn't input anything.

    * `fallback` can't be `Ellipsis`.
    * Valid formats:
      * `YYYY-MM-DD` or `YYYY/MM/DD`
      * `DD-MM-YYYY` or `DD/MM/YYYY`
      * Zeros in day and month are optional (e.g. `2024-6-5` or `5/6/2024`)
    """
    ...
def input_date(msg: str, fallback: object = ...) -> date|object:
    print()
    while 1:
        clear_last_line()
        value = input_str(msg, fallback)
        if value == fallback or not isinstance(value, str):
            return fallback

        # Try YYYY-MM-DD or YYYY/MM/DD
        match = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', value)
        if match is not None:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                continue

        # Try DD-MM-YYYY or DD/MM/YYYY
        match = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', value)
        if match is not None:
            try:
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue

##########################################################
# Selections
##########################################################
def get_selection[T](
        *options: T, input_msg: str = 'Please select an option',
        commands: dict[re.Pattern[str], Callable[[re.Match[str]], None]] = {},
        print_func: Callable[[str], None] = color_print,
        invert_print_order: bool = False
    ) -> T:
    """Shows the user a list with all the given options.
       Asks them to select one and returns it.
       
       * If `commands` is supplied, all of its patterns will be tested against the user
       input and, if one of them matches, its function will be executed.
       * `print_func` can be used to customize the list style by replacing the print
       function with a custom one.
       * If `invert_print_order` is `True`, the first options will be printed last.
    """
    return _get_selection(
        *options, input_msg=input_msg, commands=commands,
        print_func=print_func, invert_print_order=invert_print_order,
        return_index=False
    ) # type: ignore

def get_selection_index(
        *options: object, input_msg: str = 'Please select an option',
        commands: dict[re.Pattern[str], Callable[[re.Match[str]], None]] = {},
        print_func: Callable[[str], None] = color_print,
        invert_print_order: bool = False
    ) -> int:
    """Shows the user a list with all the given options.
       Asks them to select one and returns its index.
       
       * If `commands` is supplied, all of its patterns will be tested against the user
       input and, if one of them matches, its function will be executed.
       * `print_func` can be used to customize the list style by replacing the print
       function with a custom one.
       * If `invert_print_order` is `True`, the first options will be printed last.
    """
    return _get_selection(
        *options, input_msg=input_msg, commands=commands,
        print_func=print_func, invert_print_order=invert_print_order,
        return_index=True
    ) # type: ignore

def _get_selection[T](*options: T, input_msg: str,
                  commands: dict[re.Pattern[str], Callable[[re.Match[str]], None]],
                  print_func: Callable[[str], None],
                  invert_print_order: bool,
                  return_index: bool) -> T|int:

    if not invert_print_order:
        for i, option in enumerate(options):
            print_func(f'{i + 1}) {option}')
    else:
        for i, option in reversed(list(enumerate(options))):
            print_func(f'{i + 1}) {option}')

    print()
    selection = -1
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

def get_selection_from_table(
        columns: dict[str, int], options: list[list[str]],
        input_msg: str = 'Please select an option',
        commands: dict[re.Pattern[str], Callable[[re.Match[str]], None]] = {},
        invert_print_order: bool = False
    ) -> int:
    """Just like `get_selection()`, but uses `print_table()` to print the options,
    and returns the index of the selected one.
    """
    columns = {'#': 4} | columns

    # We need to make a shallow copy of the options and
    # row lists so the option index is not added to the original one
    options = copy.copy(options)
    for i, row in enumerate(options):
        row = copy.copy(row)
        row.insert(0, f'{i + 1})')
        options[i] = row

    print_table(columns, options, invert_print_order=invert_print_order)
    selection = get_selection(*options, print_func=lambda *_: None,     # type: ignore
                              input_msg=input_msg, commands=commands)

    for i, row in enumerate(options):
        if selection == row:
            return i

    raise Exception('Selection index not found')