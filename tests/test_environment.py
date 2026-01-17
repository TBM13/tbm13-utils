import unittest
from unittest.mock import MagicMock, patch

from tbm13_utils.environment import *


class TestEnvironment(unittest.TestCase):

    @patch('os.path.exists')
    def test_get_unique_file(self, mock_exists: MagicMock):
        mock_exists.return_value = False
        result = get_unique_file('test.txt')
        self.assertEqual(result, 'test.txt')
        mock_exists.assert_called_once_with('test.txt')

        # 1 conflict
        mock_exists.reset_mock()
        mock_exists.side_effect = [True, False]
        result = get_unique_file('test.txt')
        self.assertEqual(result, 'test_1.txt')
        self.assertEqual(mock_exists.call_count, 2)

        mock_exists.reset_mock()
        mock_exists.side_effect = [True, False]
        result = get_unique_file('.gitignore')
        self.assertEqual(result, '.gitignore_1')
        self.assertEqual(mock_exists.call_count, 2)

        mock_exists.reset_mock()
        mock_exists.side_effect = [True, False]
        result = get_unique_file('asd')
        self.assertEqual(result, 'asd_1')
        self.assertEqual(mock_exists.call_count, 2)

        # Multiple conflicts
        mock_exists.reset_mock()
        mock_exists.side_effect = [True, True, True, False]
        result = get_unique_file('test.txt')
        self.assertEqual(result, 'test_3.txt')
        self.assertEqual(mock_exists.call_count, 4)


if __name__ == '__main__':
    unittest.main()