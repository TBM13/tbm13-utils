import time

from .display import *
from .input import *
__all__ = [
    'ReturnNoneInterrupt', 'RetryInterrupt', 'call_retriable_func'
]

class ReturnNoneInterrupt(Exception):
    pass
class RetryInterrupt(Exception):
    pass

def call_retriable_func(func: callable, max_retries: int = -1, 
                        wait_time_between_retries: float = 0.2,
                        *args, **kwargs):
    """Calls `func` with `args` and `kwargs`, and recalls it whenever
    it raises `RetryInterrupt` up to `max_retries` times.
    
    If `max_retries` is negative, retries it infinitely.\n
    Between each retry, sleeps `wait_time_between_retries` seconds.
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

                if wait_time_between_retries > 0:
                    msg += f' in {wait_time_between_retries} seconds'
                    if max_retries > 0:
                        msg += f'. {retries_remaining()} retries remaining'

                    debug(f'{msg}...')
                    time.sleep(wait_time_between_retries)
                else:
                    debug(f'{msg}...')
        except KeyboardInterrupt:
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
                return
