import math
import os
import platform
import subprocess
import sys

from .environment import *
__all__ = [
    'title', 'style', 'get_terminal_width', 'apply_style', 'remove_style',
    'color_print', 'move_new_lines', 'decorator_print', 'info', 'info2',
    'success', 'debug', 'warn', 'error', 'clear', 'clear_last_line', 
    'print_separator', 'print_title', 'print_dict', 'print_table',
    'decorators'
]

title = ''
style = {
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
decorators = {
    'info':    '[bold][cyan][*][0][cyan] ',
    'info2':   '[bold][purple][*][0][purple] ',
    'success': '[bold][green][+][0][green] ',
    'debug':   '[bold][green][*][0][darkgray] ',
    'warn':    '[bold][yellow][!][0][yellow] ',
    'error':   '[bold][red][!][0][red] '
}

##########################################################
# Terminal Info
##########################################################
def get_terminal_width(fallback: int = 50) -> int:
    """Returns the width (columns) of the terminal.
    
    If we are running in Google Colab, returns `fallback`.
    """

    # Colab doesn't support getting the width of the output box
    if IN_COLAB:
        return fallback
    
    return os.get_terminal_size().columns

##########################################################
# Text Modifications
##########################################################
def apply_style(text: str) -> str:
    """Applies style to `text` and returns it."""

    for key, value in style.items():
        text = text.replace(f'[{key}]', value)
    return text

def remove_style(text: str) -> str:
    """Removes all style from `text` and returns it."""

    for key in style.keys():
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
    """Executes clear (Linux) or cls (Windows)."""

    if IN_COLAB:
        return

    if platform.system() == 'Windows': 
        subprocess.run(['cls'])
    else: 
        subprocess.run(['clear'])

def clear_last_line():
    """Clears the last line in the console, overwriting it."""

    if IN_COLAB:
        return

    whitespace = ' ' * get_terminal_width()
    print(f'\033[A{whitespace}\033[A')

def color_print(text: str, output=sys.stdout, end: str = '\n'):
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
    decorator_print(decorators['info'], text)
def info2(text: str):
    decorator_print(decorators['info2'], text)
def success(text: str):
    decorator_print(decorators['success'], text)
def debug(text: str):
    decorator_print(decorators['debug'], text)
def warn(text: str):
    decorator_print(decorators['warn'], text)
def error(text: str):
    decorator_print(decorators['error'], text)

def print_separator(char: str, style: str = ''):
    """Prints `char` until it fills the terminal horizontally."""

    width = get_terminal_width()
    separator = char * width
    color_print(style + separator.center(width))

def print_title(subtitle: str = '',
                separator: str = '=', style: str = '[cyan]'):
    """Calls `clear` then prints global var `title` (if not empty)
    and `subtitle` between two separators.
    """

    clear()
    if len(title) > 0 and len(subtitle) > 0:
        subtitle = ' | ' + subtitle

    print_separator(separator, style)
    color_print(f'[bold]{style}' + (title + subtitle).center(get_terminal_width()))
    print_separator(separator, style)

def print_dict(title: str, dic: dict[str, str],
               style: str = '[cyan]'):
    """Prints `title` and each key and value in `dic` with `style`."""
    color_print(f'{style}[bold][{title}]')

    format = f'{style}   '
    for key in dic.keys():
        color_print(f"{format}{key}:[0] {dic[key]}")

def print_table(columns: dict[str, int], data: list[list[str]],
                invert_print_order: bool = False):
    """Prints a table.
    
    `columns`: `Key`: Column name. `Value`: Column length.\n
    If a column's length is `0`, it'll take the biggest possible length.
    If it's `-1`, the column and its data will be ignored.

    `data`: a list of lists, where each inner list represents a row of data
    and must have the same length than `columns`.

    If `invert_print_order` is `True`, the table will be printed from bottom to top.
    """

    terminal_columns = get_terminal_width()

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
        data.reverse()

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