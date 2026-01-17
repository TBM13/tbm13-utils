import unittest
from unittest.mock import MagicMock, patch

from tbm13_utils.flow import *


class TestFlow(unittest.TestCase):

    @patch('time.sleep')
    def test_call_retriable_func(self, mock_sleep: MagicMock):
        # Test successful call (no retries)
        mock_func = MagicMock(return_value='success')
        result = call_retriable_func(mock_func)
        self.assertEqual(result, 'success')
        mock_func.assert_called_once()
        mock_sleep.assert_not_called()

        # Reset mocks
        mock_func.reset_mock()
        mock_sleep.reset_mock()

        # Test retries with success after 2 retries
        mock_func.side_effect = [RetryInterrupt, RetryInterrupt, 'success_after_retry']
        result = call_retriable_func(mock_func, max_retries=5, wait_between_retries=0.1)
        self.assertEqual(result, 'success_after_retry')
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # 2 retries

        # Reset mocks
        mock_func.reset_mock()
        mock_sleep.reset_mock()

        # Test max retries reached
        mock_func.side_effect = RetryInterrupt
        result = call_retriable_func(mock_func, max_retries=2, wait_between_retries=0.2)
        self.assertIsNone(result)
        self.assertEqual(mock_func.call_count, 3)  # initial + 2 retries
        self.assertEqual(mock_sleep.call_count, 2)

        # Reset mocks
        mock_func.reset_mock()
        mock_sleep.reset_mock()

        # Test wait multiplier
        mock_func.side_effect = [RetryInterrupt, RetryInterrupt, RetryInterrupt, 'success']
        result = call_retriable_func(mock_func, max_retries=5, wait_between_retries=0.1, wait_multiplier=2)
        self.assertEqual(result, 'success')
        self.assertEqual(mock_func.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(0.1)
        mock_sleep.assert_any_call(0.2)  # 0.1 * 2
        mock_sleep.assert_any_call(0.4)  # 0.2 * 2

        # Reset mocks
        mock_func.reset_mock()
        mock_sleep.reset_mock()

        # Test max_wait
        mock_func.side_effect = [RetryInterrupt, RetryInterrupt, RetryInterrupt, 'success']
        result = call_retriable_func(mock_func, max_retries=5, wait_between_retries=0.1, wait_multiplier=2, max_wait=0.3)
        self.assertEqual(result, 'success')
        self.assertEqual(mock_func.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(0.1)
        mock_sleep.assert_any_call(0.2)
        mock_sleep.assert_any_call(0.3)  # capped at max_wait


if __name__ == '__main__':
    unittest.main()