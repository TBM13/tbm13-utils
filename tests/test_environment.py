import unittest
from unittest.mock import MagicMock, patch

from tbm13_utils.environment import *


class TestEnvironment(unittest.TestCase):

    @patch('os.path.exists')
    def test_get_unique_file(self, mock_exists: MagicMock):
        def do_test(path: str, conflicts: int, expected: str):
            mock_exists.reset_mock()
            mock_exists.side_effect = [True] * conflicts + [False]
            result = get_unique_file(path)
            self.assertEqual(result, expected)
            self.assertEqual(mock_exists.call_count, conflicts + 1)

        # No conflicts (file does not exist)
        do_test('asd', 0, 'asd')
        do_test('test.txt', 0, 'test.txt')
        do_test('.gitignore', 0, '.gitignore')
        do_test('./test', 0, './test')
        do_test('./.gitignore', 0, './.gitignore')
        do_test('/asd/test/abc', 0, '/asd/test/abc')
        # One conflict
        do_test('asd', 1, 'asd_1')
        do_test('test.txt', 1, 'test_1.txt')
        do_test('.gitignore', 1, '.gitignore_1')
        do_test('./test', 1, './test_1')
        do_test('./.gitignore', 1, './.gitignore_1')
        do_test('/asd/test/abc.txt', 1, '/asd/test/abc_1.txt')
        # Multiple conflicts
        do_test('asd', 3, 'asd_3')
        do_test('test.txt', 3, 'test_3.txt')
        do_test('.gitignore', 3, '.gitignore_3')
        do_test('./test', 3, './test_3')
        do_test('./.gitignore', 3, './.gitignore_3')
        do_test('/asd/test/abc.txt', 3, '/asd/test/abc_3.txt')


if __name__ == '__main__':
    unittest.main()