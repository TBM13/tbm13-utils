import re
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from tbm13_utils.input import *


class TestInput(unittest.TestCase):

    @patch('builtins.input')
    def test_color_input(self, mock_input: MagicMock):
        mock_input.return_value = 'test'
        result = color_input('[red]Enter: ')
        self.assertEqual(result, 'test')
        mock_input.assert_called_once()

    def test_exception_input(self):
        try:
            raise ValueError("test error")
        except Exception as exc:
            exception_input(exc, block=False)

        try:
            raise ValueError("test error", "arg2", 6)
        except Exception as exc:
            exception_input(exc, block=False)

        try:
            raise Exception(("test error", "arg2"))
        except Exception as exc:
            exception_input(exc, block=False)

        try:
            raise ValueError(4)
        except Exception as exc:
            exception_input(exc, block=False)

    @patch('builtins.input')
    def test_ask(self, mock_input: MagicMock):
        mock_input.return_value = 'y'
        result = ask('Question?')
        self.assertTrue(result)
        mock_input.return_value = 'Y'
        result = ask('Question?')
        self.assertTrue(result)

        mock_input.return_value = 'n'
        result = ask('Question?')
        self.assertFalse(result)
        mock_input.return_value = 'N'
        result = ask('Question?')
        self.assertFalse(result)

        mock_input.return_value = ''
        result = ask('Question?', yes_default=False)
        self.assertFalse(result)
        mock_input.return_value = ''
        result = ask('Question?', yes_default=True)
        self.assertTrue(result)

    @patch('builtins.input')
    def test_input_str(self, mock_input: MagicMock):
        mock_input.return_value = 'hello'
        result = input_str('Enter string')
        self.assertEqual(result, 'hello')

        # fallback value
        mock_input.return_value = ''
        result = input_str('Enter string', 642)
        self.assertEqual(result, 642)

        mock_input.return_value = ''
        result = input_str('Enter string', 'default', min_len=50)
        self.assertEqual(result, 'default')

        # Test min_len validation
        mock_input.side_effect = ['hell', '', 'hello']
        result = input_str('Enter string', min_len=5)
        self.assertEqual(result, 'hello')

        # Test max_len validation
        mock_input.side_effect = ['this is too long for the limit', '', 'short']
        result = input_str('Enter string', max_len=10)
        self.assertEqual(result, 'short')

    @patch('builtins.input')
    def test_input_strs(self, mock_input: MagicMock):
        mock_input.return_value = 'a,b,c'
        result = input_strs('Enter strings')
        self.assertEqual(result, ['a', 'b', 'c'])

        mock_input.return_value = 'abc'
        result = input_strs('Enter strings')
        self.assertEqual(result, ['abc'])

        # fallback value
        mock_input.return_value = ''
        result = input_strs('Enter strings', ['default'])
        self.assertEqual(result, ['default'])

        # Test min_len validation
        mock_input.side_effect = ['a,b', '', 'aa,b', '', 'aa,bb']
        result = input_strs('Enter strings', min_len=2)
        self.assertEqual(result, ['aa', 'bb'])

        # Test max_len validation
        mock_input.side_effect = ['verylong,short', '', 'short,ok']
        result = input_strs('Enter strings', max_len=5)
        self.assertEqual(result, ['short', 'ok'])

    @patch('builtins.input')
    def test_input_int(self, mock_input: MagicMock):
        mock_input.return_value = '42'
        result = input_int('Enter int')
        self.assertEqual(result, 42)

        # fallback value
        mock_input.return_value = ''
        result = input_int('Enter int', 42)
        self.assertEqual(result, 42)

        mock_input.return_value = ''
        result = input_int('Enter int', 'asd')
        self.assertEqual(result, 'asd')

        # Test min validation
        mock_input.side_effect = ['5', '', '15']
        result = input_int('Enter int', min=10)
        self.assertEqual(result, 15)

        # Test max validation
        mock_input.side_effect = ['15', '', '5']
        result = input_int('Enter int', max=10)
        self.assertEqual(result, 5)

        # Test accepted_values validation
        mock_input.side_effect = ['2', '', '3']
        result = input_int('Enter int', accepted_values=[1, 3, 5])
        self.assertEqual(result, 3)

    @patch('builtins.input')
    def test_input_float(self, mock_input: MagicMock):
        mock_input.return_value = '3.14'
        result = input_float('Enter float')
        self.assertEqual(result, 3.14)

        # fallback value
        mock_input.return_value = ''
        result = input_float('Enter float', 3.14)
        self.assertEqual(result, 3.14)

        # Test min validation
        mock_input.side_effect = ['1.5', '', '4.5']
        result = input_float('Enter float', min=2.0)
        self.assertEqual(result, 4.5)

        # Test max validation
        mock_input.side_effect = ['4.5', '', '1.5']
        result = input_float('Enter float', max=3.0)
        self.assertEqual(result, 1.5)

        # Test accepted_values validation
        mock_input.side_effect = ['2.5', '', '3.5']
        result = input_float('Enter float', accepted_values=[1.0, 3.5, 5.0])
        self.assertEqual(result, 3.5)

    @patch('builtins.input')
    def test_input_ints(self, mock_input: MagicMock):
        mock_input.return_value = '1,2,3'
        result = input_ints('Enter ints')
        self.assertEqual(result, [1, 2, 3])

        mock_input.return_value = '0'
        result = input_ints('Enter ints')
        self.assertEqual(result, [0])

        # fallback value
        mock_input.return_value = ''
        result = input_ints('Enter ints', [1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

        # Test min validation
        mock_input.side_effect = ['0,5', '', '2,3']
        result = input_ints('Enter ints', min=1)
        self.assertEqual(result, [2, 3])

        # Test max validation
        mock_input.side_effect = ['5,2', '', '1,3']
        result = input_ints('Enter ints', max=4)
        self.assertEqual(result, [1, 3])

        # Test accepted_values validation
        mock_input.side_effect = ['2,5', '', '1,3']
        result = input_ints('Enter ints', accepted_values=[1, 3, 5])
        self.assertEqual(result, [1, 3])

    @patch('builtins.input')
    def test_input_floats(self, mock_input: MagicMock):
        mock_input.return_value = '1.1,2,3.3'
        result = input_floats('Enter floats')
        self.assertEqual(result, [1.1, 2.0, 3.3])

        mock_input.return_value = '0'
        result = input_floats('Enter floats')
        self.assertEqual(result, [0.0])

        # fallback value
        mock_input.return_value = ''
        result = input_floats('Enter floats', [1.1, 2.2, 3.3])
        self.assertEqual(result, [1.1, 2.2, 3.3])

        # Test min validation
        mock_input.side_effect = ['0.5,1.5', '', '1.2,2.3']
        result = input_floats('Enter floats', min=1.0)
        self.assertEqual(result, [1.2, 2.3])

        # Test max validation
        mock_input.side_effect = ['3.5,1.5', '', '1.2,2.3']
        result = input_floats('Enter floats', max=3.0)
        self.assertEqual(result, [1.2, 2.3])

        # Test accepted_values validation
        mock_input.side_effect = ['2.5,4.5', '', '1.0,3.5']
        result = input_floats('Enter floats', accepted_values=[1.0, 3.5, 5.0])
        self.assertEqual(result, [1.0, 3.5])

    @patch('builtins.input')
    def test_input_file(self, mock_input: MagicMock):
        # Valid file path
        mock_input.return_value = 'valid.txt'
        with patch('tbm13_utils.input.os.path.isfile', return_value=True):
            result = input_file('Enter file')
        self.assertEqual(result, 'valid.txt')

        # Invalid then valid
        mock_input.side_effect = ['invalid.txt', 'valid.txt']
        with patch('tbm13_utils.input.os.path.isfile', side_effect=[False, True]):
            result = input_file('Enter file')
        self.assertEqual(result, 'valid.txt')

        # Fallback with non-string
        mock_input.side_effect = None
        mock_input.return_value = ''
        result = input_file('Enter file', 99)
        self.assertEqual(result, 99)

        # Fallback with valid string
        mock_input.side_effect = None
        mock_input.return_value = ''
        with patch('tbm13_utils.input.os.path.isfile', return_value=True):
            result = input_file('Enter file', 'fallback.txt')
        self.assertEqual(result, 'fallback.txt')

        # Fallback with invalid string (recurses to valid input)
        mock_input.side_effect = ['', 'valid.txt']
        with patch('tbm13_utils.input.os.path.isfile', side_effect=[False, True]):
            result = input_file('Enter file', 'invalid.txt')
        self.assertEqual(result, 'valid.txt')

        # Fallback with non-string
        mock_input.side_effect = None
        mock_input.return_value = ''
        result = input_file('Enter file', 42)
        self.assertEqual(result, 42)

    @patch('builtins.input')
    def test_input_date(self, mock_input: MagicMock):
        # Test YYYY-MM-DD format
        mock_input.return_value = '2024-06-15'
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 6, 15))

        # Test YYYY/MM/DD format
        mock_input.return_value = '2024/06/15'
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 6, 15))

        # Test DD-MM-YYYY format
        mock_input.return_value = '15-06-2024'
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 6, 15))

        # Test DD/MM/YYYY format
        mock_input.return_value = '15/06/2024'
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 6, 15))

        # Test without leading zeros YYYY-M-D
        mock_input.return_value = '2024-6-5'
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 6, 5))

        # Test without leading zeros D/M/YYYY
        mock_input.return_value = '5/6/2024'
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 6, 5))

        # Test fallback value with empty input
        mock_input.return_value = ''
        result = input_date('Enter date', date(2023, 1, 1))
        self.assertEqual(result, date(2023, 1, 1))

        # Test fallback value with non-date type
        mock_input.return_value = ''
        result = input_date('Enter date', 'no date')
        self.assertEqual(result, 'no date')

        # Test invalid date then valid (e.g., invalid month)
        mock_input.side_effect = ['2024-13-01', '2024-12-01']
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 12, 1))

        # Test invalid date then valid (e.g., invalid day)
        mock_input.side_effect = ['2024-02-30', '2024-02-28']
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 2, 28))

        # Test invalid format then valid
        mock_input.side_effect = ['invalid', '2024-01-01']
        result = input_date('Enter date')
        self.assertEqual(result, date(2024, 1, 1))

    @patch('builtins.input')
    def test_get_selection(self, mock_input: MagicMock):
        mock_input.return_value = '1'
        with patch('tbm13_utils.input.color_print'):
            result = get_selection('option1', 'option2')
        self.assertEqual(result, 'option1')

        # Test invalid inputs then valid
        mock_input.return_value = ''
        mock_input.side_effect = ['3', '0', '-1', '2']
        with patch('tbm13_utils.input.color_print'):
            result = get_selection('option1', 'option2')
        self.assertEqual(result, 'option2')

        # Test commands
        mock_command = MagicMock()
        commands = {re.compile(r'help'): mock_command}
        mock_input.side_effect = ['help', '2']
        with patch('tbm13_utils.input.color_print'):
            result = get_selection('option1', 'option2', commands=commands)
        mock_command.assert_called_once()
        self.assertEqual(result, 'option2')

    @patch('builtins.input')
    def test_get_selection_index(self, mock_input: MagicMock):
        mock_input.return_value = '1'
        with patch('tbm13_utils.input.color_print'):
            result = get_selection_index('option1', 'option2')
        self.assertEqual(result, 0)

    @patch('builtins.input')
    def test_get_selection_from_table(self, mock_input: MagicMock):
        mock_input.return_value = '1'
        columns = {'Col1': 5, 'Col2': 5}
        options = [['a', 'b'], ['c', 'd']]
        result = get_selection_from_table(columns, options)
        self.assertEqual(result, 0)

if __name__ == '__main__':
    unittest.main()