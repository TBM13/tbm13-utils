import math
import platform
import subprocess
import sys
from typing import Sequence, TextIO

from .environment import *

__all__ = [
    'apply_style', 'remove_style',
    'color_print', 'move_new_lines', 'decorator_print', 'info', 'info2',
    'success', 'debug', 'warn', 'error', 'clear', 'clear_last_line', 
    'print_separator', 'print_title', 'print_dict', 'print_table'
]

_TITLE = ''
_STYLE = {
    # Reset
    '0':            '\033[0m',
    # Foreground
    'black':        '\033[30m',
    'red':          '\033[31m',
    'green':        '\033[32m',
    'yellow':       '\033[33m',
    'blue':         '\033[34m',
    'purple':       '\033[35m',
    'cyan':         '\033[36m',
    'darkgray':     '\033[90m',
    'white':        '\033[97m',
    # Background
    'bgBlack':     '\033[40m',
    'bgRed':       '\033[41m',
    'bgGreen':     '\033[42m',
    'bgYellow':    '\033[43m',
    'bgBlue':      '\033[44m',
    'bgPurple':    '\033[45m',
    'bgCyan':      '\033[46m',
    'bgDarkgray':  '\033[100m',
    'bgWhite':     '\033[107m',
    # Styles
    'bold':         '\033[1m',
#   'dim':          '\033[2m', # Doesn't work in Kali Linux
    'italic':       '\033[3m',
    'underline':    '\033[4m',
#   'blink':        '\033[5m', # Doesn't work in Termux
    'invert':       '\033[7m'
}

INFO_DECORATOR = '[bold][cyan][*][0][cyan] '
INFO2_DECORATOR = '[bold][purple][*][0][purple] '
SUCCESS_DECORATOR = '[bold][green][+][0][green] '
DEBUG_DECORATOR = '[bold][green][*][0][darkgray] '
WARN_DECORATOR = '[bold][yellow][!][0][yellow] '
ERROR_DECORATOR = '[bold][red][!][0][red] '

##########################################################
# Text Modifications
##########################################################
def apply_style(text: str) -> str:
    """Applies style to `text` and returns it."""

    for key, value in _STYLE.items():
        text = text.replace(f'[{key}]', value)
    return text

def remove_style(text: str) -> str:
    """Removes all style from `text` and returns it."""

    for key in _STYLE.keys():
        text = text.replace(f'[{key}]', '')
    return text

def move_new_lines(src: str, dst: str) -> tuple[str, str]:
    """Moves all newlines at the beginning of `src` to `dst`
    and returns both strings.
    """

    while src.startswith('\n'):
        src = src[1:]
        dst = '\n' + dst
    
    return (src, dst)

##########################################################
# Printing
##########################################################
def clear():
    """Executes `clear` (Linux) or `cls` (Windows)."""

    if platform.system() == 'Windows': 
        subprocess.run(['cls'], shell=True)
    else: 
        subprocess.run(['clear'])

def clear_last_line():
    """Clears the last line in the console, overwriting it."""
    print('\033[A\033[K\033[A')

def color_print(text: str, output: TextIO = sys.stdout, end: str = '\n'):
    """Applies style to `text`, appends `end` (newline by default)
    and writes it to `output`.
    """

    text += f'[0]{end}'
    text = apply_style(text)
    output.write(text)
    output.flush()

def decorator_print(decorator: str, text: str):
    """Prints `text` adding `decorator` at the beginning."""

    text, decorator = move_new_lines(text, decorator)
    color_print(decorator + text)

def info(text: str):
    decorator_print(INFO_DECORATOR, text)
def info2(text: str):
    decorator_print(INFO2_DECORATOR, text)
def success(text: str):
    decorator_print(SUCCESS_DECORATOR, text)
def debug(text: str):
    decorator_print(DEBUG_DECORATOR, text)
def warn(text: str):
    decorator_print(WARN_DECORATOR, text)
def error(text: str):
    decorator_print(ERROR_DECORATOR, text)

def print_separator(char: str, style: str = ''):
    """Prints `char` until it fills the terminal horizontally."""

    width = get_terminal_columns(10)
    separator = char * width
    color_print(style + separator.center(width))

def print_title(subtitle: str = '',
                separator: str = '=', style: str = '[cyan]'):
    """Calls `clear` then prints global var `title` (if not empty)
    and `subtitle` between two separators.
    """

    clear()
    if len(_TITLE) > 0 and len(subtitle) > 0:
        subtitle = ' | ' + subtitle

    terminal_width = get_terminal_columns(10)
    print_separator(separator, style)
    color_print(f'[bold]{style}' + (_TITLE + subtitle).center(terminal_width))
    print_separator(separator, style)

def print_dict(title: str, dic: dict[str, str],
               style: str = '[cyan]'):
    """Prints `title` and each key and value in `dic` with `style`."""
    color_print(f'{style}[bold][{title}]')

    format = f'{style}   '
    for key in dic.keys():
        color_print(f"{format}{key}:[0] {dic[key]}")

def print_table(columns: dict[str, int],
                data: Sequence[Sequence[str]],
                invert_print_order: bool = False):
    """Prints a table.
    
    * `columns` is a dictionary where:
      * `Key` is the column name.
      * `Value` is the column length.
        * If it's `0`, it'll take the biggest possible length.
        * If it's `-1`, the column and its data will be ignored.
    * `data` is a list of lists:
      * Each inner list represents a row of data and must have the same length as `columns`.

    If `invert_print_order` is `True`, the table will be printed from bottom to top.
    """
    terminal_columns = get_terminal_columns(20)

    dynamic_columns_amount = 0
    fixed_columns_size = 0
    for column_len in columns.values():
        if column_len == 0:
            dynamic_columns_amount += 1
        elif column_len > 0:
            fixed_columns_size += column_len

    dynamic_columns_len = 0
    if dynamic_columns_amount > 0:
        dynamic_columns_len = math.floor(
            (terminal_columns - fixed_columns_size) / dynamic_columns_amount
        )

    print()

    # Print header
    header = '[bold][white]'
    for name, length in columns.items():
        if length == 0:
            length = dynamic_columns_len
        elif length == -1:
            continue

        # Truncate name if needed
        if len(name) > length:
            name = name[:length - 3] + '...'

        header += '{:<{}}'.format(name, length)
    color_print(header)

    if invert_print_order:
        data = list(reversed(data))

    # Print data
    for row in data:
        row_str = ''

        for i, (name, length) in enumerate(columns.items()):
                if length == 0:
                    length = dynamic_columns_len
                elif length == -1:
                    continue

                value = remove_style(row[i])
                style = row[i].replace(value, '')

                # Truncate value if needed
                if len(value) > length:
                    value = value[:length - 3] + '...'

                row_str += style + '{:<{}}'.format(value, length)

        color_print(row_str)