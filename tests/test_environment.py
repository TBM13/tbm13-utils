import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tbm13_utils.environment import (
    get_unique_path,
    open_unique_file,
    run_and_print_output,
)


@patch("pathlib.Path.exists")
def test_get_unique_path(mock_exists: MagicMock):
    def do_test(path: str, conflicts: int, expected: str):
        mock_exists.reset_mock()
        mock_exists.side_effect = [True] * conflicts + [False]
        result = get_unique_path(path)
        assert result == Path(expected)
        assert mock_exists.call_count == conflicts + 1

    # No conflicts (file does not exist)
    do_test("asd", 0, "asd")
    do_test("test.txt", 0, "test.txt")
    do_test(".gitignore", 0, ".gitignore")
    do_test("./test", 0, "./test")
    do_test("./.gitignore", 0, "./.gitignore")
    do_test("/asd/test/abc", 0, "/asd/test/abc")
    # One conflict
    do_test("asd", 1, "asd_1")
    do_test("test.txt", 1, "test_1.txt")
    do_test(".gitignore", 1, ".gitignore_1")
    do_test("./test", 1, "./test_1")
    do_test("./.gitignore", 1, "./.gitignore_1")
    do_test("/asd/test/abc.txt", 1, "/asd/test/abc_1.txt")
    # Multiple conflicts
    do_test("asd", 3, "asd_3")
    do_test("test.txt", 3, "test_3.txt")
    do_test(".gitignore", 3, ".gitignore_3")
    do_test("./test", 3, "./test_3")
    do_test("./.gitignore", 3, "./.gitignore_3")
    do_test("/asd/test/abc.txt", 3, "/asd/test/abc_3.txt")


def test_open_unique_file(tmp_path: Path):
    def write_file(path: str, expected_path: str):
        file_handle, final_path = open_unique_file(tmp_path / path)
        with file_handle:
            file_handle.write("test")

        assert final_path.exists()
        assert final_path == tmp_path / expected_path

    # No conflicts (file does not exist)
    write_file("asd", "asd")
    write_file("test.txt", "test.txt")
    write_file(".gitignore", ".gitignore")
    write_file("./test", "./test")
    # One conflict
    write_file("asd", "asd_1")
    write_file("test.txt", "test_1.txt")
    write_file(".gitignore", ".gitignore_1")
    write_file("./test", "./test_1")
    # Two conflicts
    write_file("asd", "asd_2")
    write_file("test.txt", "test_2.txt")
    write_file(".gitignore", ".gitignore_2")
    write_file("./test", "./test_2")


def test_run_and_print_output():
    # Very simple test just to ensure the function runs and captures output correctly.
    captured_lines: list[str] = []
    args = [sys.executable, "-c", "import sys; sys.stdout.write('hello\\nworld\\n')"]
    run_and_print_output(captured_lines.append, args)

    assert captured_lines == ["hello\n", "world\n"]
