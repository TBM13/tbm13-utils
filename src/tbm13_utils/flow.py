import contextlib
import time
from typing import Callable

from .display import *
from .input import *

__all__ = [
    'ReturnInterrupt', 'RetryInterrupt',
    'handle_exceptions', 'call_retriable_func'
]

class ReturnInterrupt(Exception):
    def __init__(self, return_value):
        self.return_value = return_value

class RetryInterrupt(Exception):
    pass

@contextlib.contextmanager
def handle_exceptions(block: bool = True):
    """Wraps the code in a try-except block that catches
    and prints any exception that occurs.
    
    If `block` is True (default), the user will have to
    press ENTER to continue after the exception is printed,
    and the printed lines will be cleared after.
    """
    try:
        yield
    except (ReturnInterrupt, RetryInterrupt) as e:
        raise e
    except Exception as e:
        for i in range(exception_input(e, block)):
            if block:
                clear_last_line()

def call_retriable_func(func: Callable, max_retries: int = -1, 
                        wait_between_retries: float = 0.2,
                        wait_multiplier: float = 1,
                        max_wait: float = -1,
                        *args, **kwargs):
    """Calls `func` with `args` and `kwargs`, and recalls it whenever
    it raises `RetryInterrupt` up to `max_retries` times
    (or infinitely if `max_retries` is negative).

    Between each retry, sleeps `wait_between_retries` seconds
    and then multiplies it by `wait_multiplier`.\n
    If `max_wait` isn't negative, `wait_between_retries` will
    never exceed its value.
    """
    retries_count = 0

    def retries_remaining() -> int:
        return max_retries - retries_count + 1

    while 1:
        try:
            try:
                return func(*args, **kwargs)
            except RetryInterrupt:
                if retries_count == max_retries:
                    return
                
                retries_count += 1
                msg = 'Retrying'

                if wait_between_retries > 0:
                    if max_wait > 0 and wait_between_retries > max_wait:
                        wait_between_retries = max_wait

                    msg += f' in {wait_between_retries} seconds'
                    if max_retries > 0:
                        msg += f'. {retries_remaining()} retries remaining'

                    debug(f'{msg}...')
                    time.sleep(wait_between_retries)
                    wait_between_retries *= wait_multiplier
                else:
                    debug(f'{msg}...')
        except KeyboardInterrupt:
            # Wait a little in order to prevent EOFError
            time.sleep(0.1)

            # No retries happened so no need to ask anything,
            # as user just wants to abort the execution of func()
            if retries_count == 0:
                return

            # Lets ask just in case, user may want to pause the operation 
            # to fix whatever is causing it to fail
            try:
                if ask(f'{retries_remaining()} retries remaining. Abort?', True):
                    return
            except (KeyboardInterrupt, EOFError):
                print()
                return