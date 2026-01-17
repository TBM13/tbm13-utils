import io
import unittest
from unittest.mock import patch

from tbm13_utils.display import *


class TestDisplay(unittest.TestCase):
    def test_apply_style(self):
        text = "[red]Hello[0]"
        styled = apply_style(text)
        self.assertEqual(styled, "\033[31mHello\033[0m")

    def test_remove_style(self):
        text = "[red]Hello[0]"
        plain = remove_style(text)
        self.assertEqual(plain, "Hello")

    def test_move_new_lines(self):
        src = "\n\nHello"
        dst = "World"
        new_src, new_dst = move_new_lines(src, dst)
        self.assertEqual(new_src, "Hello")
        self.assertEqual(new_dst, "\n\nWorld")

    def test_color_print(self):
        output = io.StringIO()
        color_print("[red]Test", output=output, end="\n")
        self.assertEqual(output.getvalue(), "\033[31mTest\033[0m\n")

    def test_decorator_print(self):
        self.assertIsNone(decorator_print("[bold]>", "Message"))

    def test_info(self):
        self.assertIsNone(info("Test info"))

    def test_print_separator(self):
        with patch('tbm13_utils.display.get_terminal_columns', return_value=10):
            self.assertIsNone(print_separator("-", "[red]"))

    def test_print_dict(self):
        self.assertIsNone(print_dict("Test", {"key": "value"}))

    def test_print_table(self):
        columns = {"Col1": 5, "Col2": 0, "Col3": -1}
        data = [["A", "B", "C"], ["D", "E", "F"]]
        self.assertIsNone(print_table(columns, data))

if __name__ == '__main__':
    unittest.main()