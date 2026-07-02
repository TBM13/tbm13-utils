import re
from datetime import date
from pathlib import Path

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput

from tbm13_utils.console import (
    DateValidator,
    FloatValidator,
    IntValidator,
    ListValidator,
    PathValidator,
    SelectionValidator,
    StringValidator,
    apply_style,
    ask,
    color_input,
    color_print,
    exception,
    format_text,
    get_selection_from_table,
    print_dict,
    print_separator,
    print_table,
    print_title,
    remove_style,
)

# Move cursor to end and clear line
CLEAR_INPUT = "\x05\x15"


@pytest.fixture(autouse=True)
def pt_input():
    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        yield pipe_input


def test_format_text():
    assert format_text("Hi", 123, "asd") == "Hi 123 asd"
    assert format_text("Hi", 123, "asd", sep=", ") == "Hi, 123, asd"
    assert format_text("Hi", prefix="[bold]") == "[bold]Hi"
    assert format_text("", prefix="[bold]") == "[bold]"
    assert format_text("\n", prefix="[bold]") == "\n[bold]"
    assert format_text("\n\nHi", 123, sep=", ", prefix="[bold]") == "\n\n[bold]Hi, 123"
    assert format_text("\n", 42, None, sep="-", prefix="*") == "\n*-42-None"


def test_apply_style():
    text = "[red]Hello[0]"
    styled = apply_style(text)
    assert styled == "\x1b[31mHello\x1b[0m"


def test_remove_style():
    text = "[red]Hello[0]"
    plain = remove_style(text)
    assert plain == "Hello"


def test_color_print():
    assert color_print("[red]Test") is None


def test_color_input(pt_input: PipeInput):
    pt_input.send_text("john\n")
    assert color_input("[red]Name: ") == "john"

    # Default value
    pt_input.send_text("\n")
    assert color_input("asd: ", default="def", default_editable=False) == "def"
    # Default value with style
    pt_input.send_text("\n")
    assert color_input("asd: ", default="[bold]def", default_editable=False) == "def"
    # Unused default value
    pt_input.send_text("something\n")
    assert color_input("asd: ", default="def", default_editable=False) == "something"
    # Editable default value
    pt_input.send_text("\n")
    assert color_input("asd: ", default="def", default_editable=True) == "def"


def test_exception():
    exception(ValueError("test error"), block=False)
    exception(ValueError("test error", "arg2", 6), block=False)
    exception(Exception(("test error", "arg2")), block=False)
    exception(ValueError(4), block=False)


def test_print_separator():
    print_separator("=")


def test_print_title():
    print_title()


def test_print_dict():
    print_dict("Test", {"key": "value"})


def test_print_table():
    columns = {"Col1": 5, "Col2": 0, "Col3": -1}
    data = [["A", "B", "C"], ["D", "E", "F"]]
    print_table(columns, data)
    print_table(columns, data, invert_print_order=True)


##########################################################
# Input interactions
##########################################################
def test_ask(pt_input: PipeInput):
    # Yes
    pt_input.send_text("y\n")
    assert ask("Question?")
    pt_input.send_text("Y\n")
    assert ask("Question?")

    # No
    pt_input.send_text("n\n")
    assert not ask("Question?")
    pt_input.send_text("N\n")
    assert not ask("Question?")

    # Defaults
    pt_input.send_text("\n")
    assert not ask("Question?", yes_default=False)
    pt_input.send_text("\n")
    assert ask("Question?", yes_default=True)

    # Invalid then valid
    pt_input.send_text("invalid\nY\n")
    assert ask("Question?")


def test_get_selection_from_table(pt_input: PipeInput):
    columns = {"Name": 10, "Age": 5}
    options = [["Alice", "30"], ["Bob", "25"], ["Charlie", "35"]]

    # Select the second option
    pt_input.send_text("2\n")
    selected_index = get_selection_from_table(columns, options)
    assert selected_index == 1

    # Invalid input then select the first option
    pt_input.send_text(f"invalid\n{CLEAR_INPUT}1\n")
    selected_index = get_selection_from_table(columns, options)
    assert selected_index == 0

    # Out-of-bounds option (too low), followed by a valid option
    pt_input.send_text(f"0\n{CLEAR_INPUT}3\n")
    selected_index = get_selection_from_table(columns, options)
    assert selected_index == 2

    # Out-of-bounds option (too high), followed by a valid option
    pt_input.send_text(f"4\n{CLEAR_INPUT}1\n")
    selected_index = get_selection_from_table(columns, options)
    assert selected_index == 0


##########################################################
# Input validators
##########################################################
def test_string_validator(pt_input: PipeInput):
    """Tests the StringValidator and the base validator itself."""

    pt_input.send_text("asd\n")
    assert StringValidator().input("") == "asd"
    pt_input.send_text("\n")
    assert StringValidator().input("", default="def") == "def"

    # Min/max length
    pt_input.send_text(f"\n{CLEAR_INPUT}1\n{CLEAR_INPUT}22\n{CLEAR_INPUT}333\n")
    assert StringValidator(min_len=3).input("") == "333"
    pt_input.send_text(f"333\n{CLEAR_INPUT}22\n{CLEAR_INPUT}1\n")
    assert StringValidator(max_len=1).input("") == "1"
    # Accepted values
    pt_input.send_text(f"invalid\n{CLEAR_INPUT}valid\n")
    assert StringValidator(accepted_values=["valid"]).input("") == "valid"

    # Valid default value
    pt_input.send_text("\n")
    assert StringValidator(min_len=3, max_len=3).input("", default="def") == "def"
    # Invalid default value
    pt_input.send_text("\na\n")
    assert StringValidator(min_len=1, max_len=1).input("", default="def") == "a"


def test_validator_commands(pt_input: PipeInput):
    """Tests that commands are correctly matched, executed, and bypass validation."""

    # Test basic command execution
    validator = StringValidator()
    command_called = False

    def sample_command(match: re.Match[str]):
        nonlocal command_called
        command_called = True

    validator.commands[re.compile(r":exit")] = sample_command
    pt_input.send_text(":exit\nfinal_input\n")
    assert validator.input("") == "final_input"
    assert command_called is True

    # Test command with regex groups/arguments
    captured_args = {}

    def command_with_args(match: re.Match[str]):
        nonlocal captured_args
        captured_args = match.groupdict()

    validator.commands[re.compile(r":set (?P<key>\w+)=(?P<value>\w+)")] = (
        command_with_args
    )
    pt_input.send_text(":set timeout=30\nhello\n")
    assert validator.input("") == "hello"
    assert captured_args == {"key": "timeout", "value": "30"}

    # Test that commands bypass normal validation rules
    # Here, the validator requires at least 10 chars but our command is only 2.
    strict_validator = StringValidator(min_len=10)
    shortcut_called = False

    def shortcut_command(match: re.Match[str]):
        nonlocal shortcut_called
        shortcut_called = True

    strict_validator.commands[re.compile(r":q")] = shortcut_command
    pt_input.send_text(":q\nvalid_long_string_here\n")

    assert strict_validator.input("") == "valid_long_string_here"
    assert shortcut_called is True


def test_int_validator(pt_input: PipeInput):
    pt_input.send_text("123\n")
    assert IntValidator().input("") == 123
    pt_input.send_text("\n")
    assert IntValidator().input("", default="456") == 456
    pt_input.send_text(f"invalid\n{CLEAR_INPUT}123\n")
    assert IntValidator().input("", default="456") == 123

    # Min/max value
    pt_input.send_text(f"0\n{CLEAR_INPUT}1\n{CLEAR_INPUT}22\n{CLEAR_INPUT}100\n")
    assert IntValidator(min=100).input("") == 100
    pt_input.send_text(f"101\n{CLEAR_INPUT}100\n")
    assert IntValidator(max=100).input("") == 100

    # Accepted values
    pt_input.send_text(f"0\n{CLEAR_INPUT}4\n{CLEAR_INPUT}2\n")
    assert IntValidator(accepted_values=[1, 2, 3]).input("") == 2


def test_float_validator(pt_input: PipeInput):
    pt_input.send_text("123.45\n")
    assert FloatValidator().input("") == 123.45
    pt_input.send_text("123\n")
    assert FloatValidator().input("") == 123
    pt_input.send_text("\n")
    assert FloatValidator().input("", default="456.78") == 456.78
    pt_input.send_text(f"invalid\n{CLEAR_INPUT}123.45\n")
    assert FloatValidator().input("", default="456.78") == 123.45

    # Min/max value
    pt_input.send_text(f"0\n{CLEAR_INPUT}100.5\n")
    assert FloatValidator(min=100.5).input("") == 100.5
    pt_input.send_text(f"101.25\n{CLEAR_INPUT}100.5\n")
    assert FloatValidator(max=100.5).input("") == 100.5

    # Accepted values
    pt_input.send_text(f"0\n{CLEAR_INPUT}4.5\n{CLEAR_INPUT}2.25\n")
    assert FloatValidator(accepted_values=[1.0, 2.25, 3.75]).input("") == 2.25


def test_path_validator(pt_input: PipeInput, tmp_path: Path):
    # Setup temp files/dirs
    existing_file = tmp_path / "test_file.txt"
    existing_file.write_text("content")
    existing_dir = tmp_path / "test_dir"
    existing_dir.mkdir()
    non_existent_path = tmp_path / "does_not_exist.txt"

    # Default: Path must NOT exist
    pt_input.send_text(f"{non_existent_path}\n")
    assert PathValidator().input("") == str(non_existent_path)
    pt_input.send_text(f"{existing_file}\n{CLEAR_INPUT}{non_existent_path}\n")
    assert PathValidator().input("") == str(non_existent_path)

    # Path must exist and must be a file
    pt_input.send_text(
        f"{non_existent_path}\n{CLEAR_INPUT}{existing_dir}\n{CLEAR_INPUT}{existing_file}\n"
    )
    assert PathValidator(must_exist_as_file=True).input("") == str(existing_file)

    # Path must exist and must be a directory
    pt_input.send_text(
        f"{non_existent_path}\n{CLEAR_INPUT}{existing_file}\n{CLEAR_INPUT}{existing_dir}\n"
    )
    assert PathValidator(must_exist_as_dir=True).input("") == str(existing_dir)


def test_date_validator(pt_input: PipeInput):
    # Test YYYY-MM-DD format
    pt_input.send_text("2026-07-01\n")
    assert DateValidator().input("") == date(2026, 7, 1)
    # Test YYYY/MM/DD format
    pt_input.send_text("2026/07/02\n")
    assert DateValidator().input("") == date(2026, 7, 2)
    # Without leading zeros
    pt_input.send_text("2026/7/3\n")
    assert DateValidator().input("") == date(2026, 7, 3)

    # Test DD-MM-YYYY format
    pt_input.send_text("03-07-2026\n")
    assert DateValidator().input("") == date(2026, 7, 3)
    # Test DD/MM/YYYY format
    pt_input.send_text("04/07/2026\n")
    assert DateValidator().input("") == date(2026, 7, 4)
    # Without leading zeros
    pt_input.send_text("5/7/2026\n")
    assert DateValidator().input("") == date(2026, 7, 5)

    # Invalid string followed by a valid date
    pt_input.send_text(f"not-a-date\n{CLEAR_INPUT}2026-07-01\n")
    assert DateValidator().input("") == date(2026, 7, 1)
    # Valid date format but invalid calendar date (e.g., February 30th)
    # followed by a valid date
    pt_input.send_text(f"2026-02-30\n{CLEAR_INPUT}2026-07-01\n")
    assert DateValidator().input("") == date(2026, 7, 1)


def test_selection_validator(pt_input: PipeInput):
    options = ["Apple", "Banana", "Cherry"]

    # First option
    pt_input.send_text("1\n")
    assert SelectionValidator().input(*options) == 0
    # Last option
    pt_input.send_text("3\n")
    assert SelectionValidator().input(*options) == 2

    # Invalid input then second option
    pt_input.send_text(f"abc\n{CLEAR_INPUT}2\n")
    assert SelectionValidator().input(*options) == 1

    # Out-of-bounds option (too low), followed by a valid option
    pt_input.send_text(f"0\n{CLEAR_INPUT}1\n")
    assert SelectionValidator().input(*options) == 0
    # Out-of-bounds option (too high), followed by a valid option
    pt_input.send_text(f"4\n{CLEAR_INPUT}3\n")
    assert SelectionValidator().input(*options) == 2


def test_list_validator(pt_input: PipeInput):
    # Basic valid list of integers
    pt_input.send_text("1,2,3\n")
    assert ListValidator(IntValidator()).input("") == [1, 2, 3]
    # Trailing separator is automatically stripped
    pt_input.send_text("4,5,\n")
    assert ListValidator(IntValidator()).input("") == [4, 5]
    # Empty list
    pt_input.send_text("\n")
    assert ListValidator(IntValidator()).input("") == []

    # Invalid structure: starting with a separator
    # leading separator (invalid) -> clears -> sends valid items
    pt_input.send_text(f",1,2\n{CLEAR_INPUT}1,2\n")
    assert ListValidator(IntValidator()).input("") == [1, 2]

    # Minimum items constraint
    # 1 item (invalid) -> clears -> 2 items (valid)
    pt_input.send_text(f"1\n{CLEAR_INPUT}1,2\n")
    assert ListValidator(IntValidator(), min_items=2).input("") == [1, 2]
    # Maximum items constraint
    # 3 items (invalid) -> clears -> 2 items (valid)
    pt_input.send_text(f"1,2,3\n{CLEAR_INPUT}1,2\n")
    assert ListValidator(IntValidator(), max_items=2).input("") == [1, 2]

    # Underlying item validator failure
    # Invalid string item "abc" -> clears -> valid integers
    pt_input.send_text(f"1,abc,3\n{CLEAR_INPUT}1,2,3\n")
    assert ListValidator(IntValidator()).input("") == [1, 2, 3]

    # Custom item separator
    pt_input.send_text("10;20;30\n")
    assert ListValidator(IntValidator(), item_separator=";").input("") == [10, 20, 30]
