import copy
import math
import os
import re
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable, Container, Sequence
from datetime import date
from typing import Any, TextIO, final, override

from prompt_toolkit import ANSI, PromptSession, print_formatted_text
from prompt_toolkit.application import get_app_session
from prompt_toolkit.document import Document
from prompt_toolkit.history import History, InMemoryHistory
from prompt_toolkit.shortcuts import clear, set_title
from prompt_toolkit.validation import ValidationError, Validator

from .typing import inherits_args1

__all__ = [
    "BaseValidator",
    "DateValidator",
    "FloatValidator",
    "IntValidator",
    "ListValidator",
    "PathValidator",
    "SelectionValidator",
    "StringValidator",
    "apply_style",
    "ask",
    "clear",
    "clear_lines",
    "color_input",
    "color_print",
    "debug",
    "error",
    "exception",
    "format_text",
    "get_terminal_columns",
    "get_terminal_rows",
    "info",
    "info2",
    "print_dict",
    "print_separator",
    "print_table",
    "print_title",
    "remove_style",
    "success",
    "warn",
]

TITLE = ""
_STYLE = {
    # Reset
    "0": "\033[0m",
    # Foreground
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "purple": "\033[35m",
    "cyan": "\033[36m",
    "darkgray": "\033[90m",
    "white": "\033[97m",
    # Background
    "bgBlack": "\033[40m",
    "bgRed": "\033[41m",
    "bgGreen": "\033[42m",
    "bgYellow": "\033[43m",
    "bgBlue": "\033[44m",
    "bgPurple": "\033[45m",
    "bgCyan": "\033[46m",
    "bgDarkgray": "\033[100m",
    "bgWhite": "\033[107m",
    # Styles
    "bold": "\033[1m",
    #   'dim':          '\033[2m', # Doesn't work in Kali Linux
    "italic": "\033[3m",
    "underline": "\033[4m",
    #   'blink':        '\033[5m', # Doesn't work in Termux
    "invert": "\033[7m",
}

INFO_DECORATOR = "[bold][cyan][*][0][cyan] "
INFO2_DECORATOR = "[bold][purple][*][0][purple] "
SUCCESS_DECORATOR = "[bold][green][+][0][green] "
DEBUG_DECORATOR = "[bold][green][*][0][darkgray] "
WARN_DECORATOR = "[bold][yellow][!][0][yellow] "
ERROR_DECORATOR = "[bold][red][!][0][red] "
ASK_DECORATOR = "[bold][blue][?][0] "


##########################################################
# Text Modifications
##########################################################
def format_text(*values: Any, sep: str = " ", prefix: str = "") -> str:
    """Joins the given values using the specified separator
    and returns them as a string.

    `prefix` is prepended to the text, preserving newlines at the start.
    """

    text = sep.join(str(value) for value in values)
    if prefix:
        original_len = len(text)
        text = text.lstrip("\n")
        start_newlines = original_len - len(text)
        text = "\n" * start_newlines + prefix + text

    return text


def apply_style(text: str) -> str:
    """Applies style to `text` and returns it."""

    for key, value in _STYLE.items():
        text = text.replace(f"[{key}]", value)

    return text


def remove_style(text: str) -> str:
    """Removes all style from `text` and returns it."""

    for key in _STYLE:
        text = text.replace(f"[{key}]", "")
    return text


##########################################################
# Terminal interaction
##########################################################
_default_history = InMemoryHistory()


def get_terminal_columns() -> int:
    """Gets the current number of columns in the terminal."""
    return get_app_session().output.get_size().columns


def get_terminal_rows() -> int:
    """Gets the current number of rows in the terminal."""
    return get_app_session().output.get_size().rows


def clear_lines(amount: int):
    """Clears the last X lines in the console, overwriting them."""
    if amount <= 0:
        return

    output = get_app_session().output
    output.cursor_up(amount)
    output.write("\r")
    output.erase_down()
    output.flush()


def color_print(
    *values: Any,
    sep: str = " ",
    prefix: str = "",
    postfix: str = "",
    file: TextIO | None = None,
    end: str = "\n",
    flush: bool = False,
):
    """Formats the given values, applies style to them
    and prints them to the specified output.
    """
    text = format_text(*values, sep=sep, prefix=prefix) + postfix
    ansi_text = ANSI(apply_style(text))

    print_formatted_text(ansi_text, file=file, end=end, flush=flush)


def color_input(
    # Left prompt
    *values: Any,
    sep: str = " ",
    prefix: str = "",
    postfix: str = "",
    # Other prompts/info
    rprompt: str = "",
    bottom_toolbar: str = "",
    # Input defaults
    default: str = "",
    default_editable: bool = False,
    # Other
    history: History | None = None,
    show_frame: bool = False,
):
    """Formats the given values, applies style to them
    and asks the user to input a string using them as the prompt.

    :param rprompt: Right prompt (displayed on the right side of the input line).
    :param bottom_toolbar: Text displayed below the input line (on the next line).
                           Colors are inverted: Foreground becomes background
                           and viceversa.
    :param default: Default value.
                    Can only have style when `default_editable` is `False`.
    :param default_editable: If `True`, the default value is editable by the user.
                             Otherwise, it is displayed as a placeholder and hidden
                             when the user starts typing.
    :param history: The input history. If `None`, a default history is used.
    :param show_frame: If `True`, shows a frame around the input line.
    """
    return _color_input(
        *values,
        sep=sep,
        prefix=prefix,
        postfix=postfix,
        rprompt=rprompt,
        bottom_toolbar=bottom_toolbar,
        default=default,
        default_editable=default_editable,
        history=history,
        show_frame=show_frame,
    )


def _color_input(
    # Left prompt
    *values: Any,
    sep: str = " ",
    prefix: str = "",
    postfix: str = "",
    # Other prompts/info
    rprompt: str = "",
    bottom_toolbar: str = "",
    # Input defaults
    default: str = "",
    default_editable: bool = False,
    # Other
    history: History | None = None,
    show_frame: bool = False,
    validator: Validator | None = None,
) -> str:
    lprompt = apply_style(format_text(*values, sep=sep, prefix=prefix) + postfix)
    if rprompt:
        rprompt = apply_style(format_text(rprompt))
    if bottom_toolbar:
        bottom_toolbar = apply_style(format_text(bottom_toolbar))
    if default and not default_editable:
        styled_default = apply_style(format_text(default, prefix="[darkgray]"))
    else:
        styled_default = ""

    # Avoid using a shared session since styles might be preserved between
    # different prompts
    session: PromptSession[str] = PromptSession(history=history or _default_history)

    res = session.prompt(
        ANSI(lprompt),
        # Other prompts
        rprompt=ANSI(rprompt) if rprompt else None,
        bottom_toolbar=ANSI(bottom_toolbar) if bottom_toolbar else None,
        # Defaults
        default=default if default_editable else "",
        placeholder=ANSI(styled_default) if default and not default_editable else None,
        # Validation
        validator=validator,
        # Other
        show_frame=show_frame,
    )

    if not res and default and not default_editable:
        return remove_style(default)

    return res


##########################################################
# Printing
##########################################################
def info(*values: Any, block: bool = False):
    if not block:
        color_print(*values, prefix=INFO_DECORATOR)
    else:
        color_input(*values, prefix=INFO_DECORATOR, postfix="[0] [darkgray][Enter][0]")


def info2(*values: Any, block: bool = False):
    if not block:
        color_print(*values, prefix=INFO2_DECORATOR)
    else:
        color_input(*values, prefix=INFO2_DECORATOR, postfix="[0] [darkgray][Enter][0]")


def success(*values: Any, block: bool = False):
    if not block:
        color_print(*values, prefix=SUCCESS_DECORATOR)
    else:
        color_input(*values, prefix=SUCCESS_DECORATOR, postfix="[0] [white][Enter][0]")


def debug(*values: Any, block: bool = False):
    if not block:
        color_print(*values, prefix=DEBUG_DECORATOR)
    else:
        color_input(*values, prefix=DEBUG_DECORATOR, postfix="[0] [darkgray][Enter][0]")


def warn(*values: Any, block: bool = False):
    if not block:
        color_print(*values, prefix=WARN_DECORATOR)
    else:
        color_input(*values, prefix=WARN_DECORATOR, postfix="[0] [darkgray][Enter][0]")


def error(*values: Any, block: bool = False):
    if not block:
        color_print(*values, prefix=ERROR_DECORATOR)
    else:
        color_input(*values, prefix=ERROR_DECORATOR, postfix="[0] [darkgray][Enter][0]")


def exception(ex: Exception, message: str = "Abort", block: bool = True) -> int:
    """Prints the exception's args and the
    file, method and line where it was raised.

    Returns the number of printed lines.
    """
    print()
    printed_lines = 1

    tb = traceback.extract_tb(ex.__traceback__)
    tb = tb[-1] if len(tb) > 0 else None
    args = ex.args
    msg = ex.__class__.__name__
    details = tb.line or "" if tb is not None else ""
    if len(ex.args) == 1:
        args = ex.args[0]

    if isinstance(args, tuple):
        if len(args) == 0:  # type: ignore
            if not isinstance(ex, AssertionError):
                details = ""
        elif isinstance(args[0], str):
            msg = args[0]
            details = ",".join(repr(arg) for arg in args[1:])  # type: ignore
        else:
            details = ",".join(repr(arg) for arg in args)  # type: ignore
    elif isinstance(args, str):
        if len(args) > 0:
            msg = args
            details = ""
    else:
        details = repr(args)

    if len(details) > 0:
        if len(details) <= 60:
            msg += f": [darkgray]{details}"
        else:
            debug(repr(details))
            printed_lines += 1

    if tb is not None:
        filename = os.path.basename(tb.filename)
        msg = f"{message}[darkgray]({tb.name}@{filename}:{tb.lineno})[red]: {msg}"
    else:
        msg = f"{message}: {msg}"
    error(msg, block=block)

    printed_lines += 1
    return printed_lines


def print_separator(sep: str, style: str = ""):
    """Prints the separator until it fills the terminal horizontally."""
    raw_sep = remove_style(sep) or " "

    columns = get_terminal_columns()
    sep = sep * (columns // len(raw_sep))
    color_print(style + sep)


def print_title(subtitle: str = "", separator: str = "=", style: str = "[cyan]"):
    """Clears the terminal and prints the global variable `TITLE`
    surrounded by separators, with an optional subtitle and style.
    """

    clear()
    full_title = TITLE
    if full_title and subtitle:
        full_title += " | "
    if subtitle:
        full_title += subtitle

    set_title(full_title)

    columns = get_terminal_columns()
    print_separator(separator, style)
    color_print(f"[bold]{style}" + full_title.center(columns))
    print_separator(separator, style)


def print_dict(title: str, dic: dict[str, str], style: str = "[cyan]"):
    """Prints `title` and each key and value in `dic` with `style`."""
    color_print(f"{style}[bold][{title}]")

    style = f"{style}   "
    for key, value in dic.items():
        color_print(f"{style}{key}:[0] {value}")


def print_table(
    columns: dict[str, int],
    data: Sequence[Sequence[str]],
    invert_print_order: bool = False,
):
    """Prints a table.

    * `columns` is a dictionary where:
      * `Key` is the column name.
      * `Value` is the column length.
        * If it's `0`, it'll take the biggest possible length.
        * If it's `-1`, the column and its data will be ignored.
    * `data` is a list of lists:
      * Each inner list represents a row of data and must have the same length
      as `columns`.

    If `invert_print_order` is `True`, the table will be printed from bottom to top.
    """
    terminal_cols = get_terminal_columns()

    dynamic_cols_amount = 0
    fixed_columns_size = 0
    for col_len in columns.values():
        if col_len == 0:
            dynamic_cols_amount += 1
        elif col_len > 0:
            fixed_columns_size += col_len

    dynamic_cols_len = 0
    if dynamic_cols_amount > 0:
        dynamic_cols_len = math.floor(
            (terminal_cols - fixed_columns_size) / dynamic_cols_amount
        )

    print()

    # Print header
    header = "[bold][white]"
    for raw_name, raw_len in columns.items():
        if raw_len == -1:
            continue

        name = raw_name
        length = dynamic_cols_len if raw_len == 0 else raw_len

        # Truncate name if needed
        if len(name) > length:
            name = name[: length - 3] + "..."

        header += "{:<{}}".format(name, length)
    color_print(header)

    if invert_print_order:
        data = list(reversed(data))

    # Print data
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    for row in data:
        row_str = ""

        for i, raw_len in enumerate(columns.values()):
            if raw_len == -1:
                continue

            length = dynamic_cols_len if raw_len == 0 else raw_len

            value = apply_style(row[i])
            ansi_spans: dict[int, str] = {}
            for match in ansi_escape.finditer(value):
                ansi_spans[match.start()] = match.group()

            # Remove ANSI escape sequences
            value = ansi_escape.sub("", value)

            # Truncate value if needed
            if len(value) > length:
                value = value[: length - 3] + "..."

            value = "{:<{}}".format(value, length)
            # Reinsert ANSI escape sequences
            for pos, code in ansi_spans.items():
                value = value[:pos] + code + value[pos:]

            row_str += value

        color_print(row_str)


##########################################################
# Input interactions
##########################################################
def ask(question: str, yes_default: bool = False) -> bool:
    """Asks the user to input Yes or No (Y/N).
    Returns `True` when the answer is Yes.

    If `yes_default` is `True`, yes will be selected
    when the user doesn't input anything.
    """
    postfix = " [cyan]" + ("[Y/n]" if yes_default else "[y/N]")
    text = apply_style(
        format_text(
            question,
            sep=" ",
            prefix=ASK_DECORATOR,
        )
        + postfix
    )

    while True:
        selection = color_input(text).upper()

        if len(selection) == 0:
            return yes_default
        if selection != "Y" and selection != "N":
            clear_lines(1)
            continue

        return selection == "Y"


def get_selection_from_table(
    columns: dict[str, int],
    options: list[list[str]],
    prompt: str = "\n[darkgray]Please select an option",
    commands: dict[re.Pattern[str], Callable[[re.Match[str]], None]] | None = None,
    invert_print_order: bool = False,
) -> int:
    """Prints all the options in a table and asks the user to select one of them.

    Returns the index of the selected option.
    """
    columns = {"#": 4} | columns

    # We need to make a shallow copy of the options and
    # row lists so the option index is not added to the original one
    options = copy.copy(options)
    for i, row in enumerate(options):
        row_clone = copy.copy(row)
        row_clone.insert(0, f"{i + 1})")
        options[i] = row_clone

    print_table(columns, options, invert_print_order=invert_print_order)
    validator = IntValidator(min=1, max=len(options))
    validator.commands = commands or {}
    return validator.input(prompt) - 1


##########################################################
# Input validators
##########################################################
class BaseValidator[T](Validator, ABC):
    """A base class for input validators that provide an input method
    which validates & parses the user input, and supports style & commands.
    """

    def __init__(self):
        super().__init__()

        self.commands: dict[re.Pattern[str], Callable[[re.Match[str]], Any]] = {}
        """When the user input matches the pattern, the corresponding
        function will be executed instead of validating and parsing the input.

        Only applies when using the `input()` method of this validator.
        """
        self.__default: str = ""

    def _prepare_input_prompt(self, *args: Any) -> tuple[Any, ...]:
        """Override this to customize the prompt shown to the user.

        The default behavior is to append a colon and space (": ") to the prompt
        if the last arg is not a string or ends with an alphanumeric character.
        """
        if len(args) > 0 and (
            (not isinstance(args[-1], str))
            or (len(args[-1]) > 0 and args[-1][-1].isalnum())
        ):
            args = (*args[:-1], str(args[-1]) + ": ")

        return args

    @abstractmethod
    def _validate(self, text: str):
        """Validates the input. If invalid, this should raise a `ValidationError`."""
        ...

    @abstractmethod
    def _parse(self, user_input: str) -> T:
        """Converts a validated input string into the desired type."""
        ...

    def __match_command(
        self, user_input: str
    ) -> tuple[Callable[[re.Match[str]], Any], re.Match[str]] | None:
        """Tries to match the user input against all registered commands."""
        for pattern, func in self.commands.items():
            match = pattern.fullmatch(user_input)
            if match is not None:
                return func, match

        return None

    @final
    def validate(self, document: Document):
        # If the input is a command, do not proceed with validation
        if self.__match_command(document.text) is None:
            text = document.text or self.__default
            try:
                self._validate(text)
            except ValidationError as e:
                raise ValidationError(
                    message=e.message,
                    # Correct cursor position if the default (placeholder) value is used
                    cursor_position=e.cursor_position if document.text else 0,
                ) from e

    @inherits_args1(color_input)
    @final
    def input(self, *args: Any, **kwargs: Any) -> T:
        if "validator" in kwargs:
            raise ValueError("Validator specified on a validator's input method")

        args = self._prepare_input_prompt(*args)

        # A default non-editable value is shown as a placeholder
        # and is not something actually written in the user's input line.
        # So we need to store it and use it when validating an empty input
        default = kwargs.get("default", "")
        default_editable = kwargs.get("default_editable", False)
        if default and not default_editable:
            self.__default = default

        while True:
            user_input = _color_input(*args, validator=self, **kwargs)
            cmd_match = self.__match_command(user_input)
            if cmd_match is not None:
                func, match = cmd_match
                func(match)
                continue

            break

        return self._parse(user_input)


class ListValidator[T](BaseValidator[list[T]]):
    def __init__(
        self,
        item_validator: BaseValidator[T],
        item_separator: str = ",",
        min_items: int = 0,
        max_items: int | None = None,
    ):
        super().__init__()

        self.item_validator = item_validator
        self.item_separator = item_separator
        self.min_items = min_items
        self.max_items = max_items

    @override
    def _prepare_input_prompt(self, *args: Any):
        # Let the item validator prepare the prompt as it
        # might do something special like printing a list of options
        return self.item_validator._prepare_input_prompt(*args)

    @override
    def _validate(self, text: str):
        if text.startswith(self.item_separator):
            raise ValidationError(
                message="Invalid value", cursor_position=len(self.item_separator)
            )

        text = text.removesuffix(self.item_separator)
        items = text.split(self.item_separator) if text else []

        if len(items) < self.min_items:
            raise ValidationError(
                message=f"List must have at least {self.min_items} "
                + ("item" if self.min_items == 1 else "items"),
                cursor_position=len(text),
            )
        if self.max_items is not None and len(items) > self.max_items:
            raise ValidationError(
                message=f"List must have at most {self.max_items} "
                + ("item" if self.max_items == 1 else "items"),
                cursor_position=len(text),
            )

        current_pos = 0
        for item in items:
            current_pos += len(item)
            try:
                self.item_validator._validate(item)
            except ValidationError as e:
                raise ValidationError(
                    message=f"Invalid item '{item}': {e.message}",
                    cursor_position=current_pos,
                ) from e

            current_pos += len(self.item_separator)

    @override
    def _parse(self, user_input: str) -> list[T]:
        user_input = user_input.removesuffix(self.item_separator)
        if not user_input:
            return []

        items = user_input.split(self.item_separator)
        return [self.item_validator._parse(item) for item in items]


class SelectionValidator(BaseValidator[int]):
    def __init__(
        self,
        prompt: str = "\n[darkgray]Select an option",
        fmt: str = "\n{index}) {item}",
    ):
        super().__init__()

        self.prompt = "\n" + prompt
        self.fmt = fmt
        self._item_count = 0

    @override
    def _prepare_input_prompt(self, *args: Any):
        self._item_count = len(args)
        args = (
            *(self.fmt.format(index=i + 1, item=arg) for i, arg in enumerate(args)),
            self.prompt,
        )
        return super()._prepare_input_prompt(*args)

    @override
    def _validate(self, text: str):
        try:
            value = int(text)
        except ValueError as ex:
            raise ValidationError(
                message="Invalid option", cursor_position=len(text)
            ) from ex

        if value < 1 or value > self._item_count:
            raise ValidationError(
                message=f"The option must be between 1 and {self._item_count}",
                cursor_position=len(text),
            )

    @override
    def _parse(self, user_input: str) -> int:
        return int(user_input) - 1


class TableSelectionValidator(BaseValidator[int]):
    def __init__(self, prompt: str = "\n[darkgray]Select an option"):
        super().__init__()

        self.prompt = "\n" + prompt


class StringValidator(BaseValidator[str]):
    def __init__(
        self,
        min_len: int = 0,
        max_len: int | None = None,
        accepted_values: Container[str] | None = None,
    ):
        super().__init__()

        self.min_len = min_len
        self.max_len = max_len
        self.accepted_values = accepted_values

    @override
    def _validate(self, text: str):
        if len(text) < self.min_len:
            raise ValidationError(
                message=f"Input must have at least {self.min_len} "
                + ("char" if self.min_len == 1 else "chars"),
                cursor_position=len(text),
            )
        if self.max_len is not None and len(text) > self.max_len:
            raise ValidationError(
                message=f"Input must have at most {self.max_len} "
                + ("char" if self.max_len == 1 else "chars"),
                cursor_position=len(text),
            )
        if self.accepted_values is not None and text not in self.accepted_values:
            raise ValidationError(
                message=f"Input must be one of {self.accepted_values}",
                cursor_position=len(text),
            )

    @override
    def _parse(self, user_input: str) -> str:
        return user_input


class NumberValidator[T: int | float](BaseValidator[T], ABC):
    type: type[T]

    def __init__(
        self,
        min: T | None = None,
        max: T | None = None,
        accepted_values: Container[T] | None = None,
    ):
        super().__init__()

        self.min = min
        self.max = max
        self.accepted_values = accepted_values

    @override
    def _validate(self, text: str):
        try:
            value = self.type(text)
        except ValueError as ex:
            raise ValidationError(
                message=f"The input must be a valid {self.type.__name__}",
                cursor_position=len(text),
            ) from ex

        if self.min is not None and value < self.min:
            raise ValidationError(
                message=f"The number must be at least {self.min}",
                cursor_position=len(text),
            )
        if self.max is not None and value > self.max:
            raise ValidationError(
                message=f"The number must be at most {self.max}",
                cursor_position=len(text),
            )
        if self.accepted_values is not None and value not in self.accepted_values:
            raise ValidationError(
                message=f"The number must be one of {self.accepted_values}",
                cursor_position=len(text),
            )

    @override
    def _parse(self, user_input: str) -> T:
        return self.type(user_input)


class IntValidator(NumberValidator[int]):
    type = int


class FloatValidator(NumberValidator[float]):
    type = float


class PathValidator(BaseValidator[str]):
    """A validator for file and directory paths."""

    def __init__(
        self,
        must_exist_as_file: bool = False,
        must_exist_as_dir: bool = False,
    ):
        super().__init__()

        self.must_exist_as_file = must_exist_as_file
        self.must_exist_as_dir = must_exist_as_dir

    @override
    def _validate(self, text: str):
        if self.must_exist_as_file and not os.path.isfile(text):
            raise ValidationError(
                message="The file must exist", cursor_position=len(text)
            )
        if self.must_exist_as_dir and not os.path.isdir(text):
            raise ValidationError(
                message="The directory must exist", cursor_position=len(text)
            )
        if (
            not self.must_exist_as_file
            and not self.must_exist_as_dir
            and os.path.exists(text)
        ):
            raise ValidationError(
                message="The path already exists", cursor_position=len(text)
            )

    @override
    def _parse(self, user_input: str) -> str:
        return user_input


class DateValidator(BaseValidator[date]):
    """A validator for date input in the formats `YYYY-MM-DD`, `YYYY/MM/DD`,
    `DD-MM-YYYY` or `DD/MM/YYYY`.
    """

    _pattern1 = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$")
    """`YYYY-MM-DD` or `YYYY/MM/DD`."""
    _pattern2 = re.compile(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$")
    """`DD-MM-YYYY` or `DD/MM/YYYY`."""

    @override
    def _validate(self, text: str):
        try:
            self._parse(text)
        except ValueError as ex:
            raise ValidationError(
                message="The input must be a valid date", cursor_position=len(text)
            ) from ex

    @override
    def _parse(self, user_input: str) -> date:
        # Try YYYY-MM-DD or YYYY/MM/DD
        match = self._pattern1.match(user_input)
        if match is not None:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

        # Try DD-MM-YYYY or DD/MM/YYYY
        match = self._pattern2.match(user_input)
        if match is not None:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))

        raise ValueError("Not a known date format")
