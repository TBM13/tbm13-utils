from unittest.mock import MagicMock, patch

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from tbm13_utils.flow import RetryInterrupt, call_retriable_func


@pytest.fixture(autouse=True)
def pt_input():
    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        yield pipe_input


@patch("time.sleep")
def test_call_retriable_func(mock_sleep: MagicMock):
    # Test successful call (no retries)
    mock_func = MagicMock(return_value="success")
    result = call_retriable_func(mock_func)
    assert result == "success"
    mock_func.assert_called_once()
    mock_sleep.assert_not_called()

    # Reset mocks
    mock_func.reset_mock()
    mock_sleep.reset_mock()

    # Test retries with success after 2 retries
    mock_func.side_effect = [RetryInterrupt, RetryInterrupt, "success_after_retry"]
    result = call_retriable_func(mock_func, max_retries=5, wait_between_retries=0.1)
    assert result == "success_after_retry"
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2  # 2 retries

    # Reset mocks
    mock_func.reset_mock()
    mock_sleep.reset_mock()

    # Test max retries reached
    mock_func.side_effect = RetryInterrupt
    result = call_retriable_func(mock_func, max_retries=2, wait_between_retries=0.2)
    assert result is None
    assert mock_func.call_count == 3  # initial + 2 retries
    assert mock_sleep.call_count == 2

    # Reset mocks
    mock_func.reset_mock()
    mock_sleep.reset_mock()

    # Test wait multiplier
    mock_func.side_effect = [
        RetryInterrupt,
        RetryInterrupt,
        RetryInterrupt,
        "success",
    ]
    result = call_retriable_func(
        mock_func, max_retries=5, wait_between_retries=0.1, wait_multiplier=2
    )
    assert result == "success"
    assert mock_func.call_count == 4
    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(0.1)
    mock_sleep.assert_any_call(0.2)  # 0.1 * 2
    mock_sleep.assert_any_call(0.4)  # 0.2 * 2

    # Reset mocks
    mock_func.reset_mock()
    mock_sleep.reset_mock()

    # Test max_wait
    mock_func.side_effect = [
        RetryInterrupt,
        RetryInterrupt,
        RetryInterrupt,
        "success",
    ]
    result = call_retriable_func(
        mock_func,
        max_retries=5,
        wait_between_retries=0.1,
        wait_multiplier=2,
        max_wait=0.3,
    )
    assert result == "success"
    assert mock_func.call_count == 4
    assert mock_sleep.call_count == 3
    mock_sleep.assert_any_call(0.1)
    mock_sleep.assert_any_call(0.2)
    mock_sleep.assert_any_call(0.3)  # capped at max_wait
