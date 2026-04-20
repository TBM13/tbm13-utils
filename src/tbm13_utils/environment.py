import os
import signal
import subprocess
import time
from subprocess import CompletedProcess, Popen
from typing import Any, Callable

__all__ = [
    'get_terminal_columns', 'get_unique_file',
    'run_as_root', 'popen_as_root', 'run_and_print_output'
]

def get_terminal_columns(fallback: int) -> int:
    """Returns the number of columns in the terminal.

    If something goes wrong, returns `fallback`.
    """
    try:
        return os.get_terminal_size().columns
    except Exception:
        return fallback

def get_unique_file(file_path: str) -> str:
    """Generates an unique file name for `file_path` and returns it.
    
    If `file_path` does not exist, returns it as-is.
    Otherwise, appends a number to it.
    """

    base_name = os.path.basename(file_path)
    extension_index = base_name.rfind('.')
    if extension_index <= 0:
        # Dot being at the start (e.g. on '.bashrc') counts as no extension
        extension = ''
    else:
        extension = base_name[extension_index:]
        file_path = file_path[:extension_index]

    unique_path = file_path + extension
    i = 1
    while os.path.exists(unique_path):
        unique_path = f"{file_path}_{i}{extension}"
        i += 1
    
    return unique_path

def run_as_root(args: list[str], **kwargs: Any) -> CompletedProcess[Any]:
    """Calls `subprocess.run` with `args` and `kwargs`.
    
    If the current user isn't root, prepend the command with `sudo`.
    """
    if os.geteuid() != 0:                   # type: ignore
        args = ['sudo'] + args

    return subprocess.run(args, **kwargs)   # type: ignore

def popen_as_root(args: list[str], **kwargs: Any) -> Popen[Any]:
    """Calls `subprocess.Popen` with `args` and `kwargs`.
    
    If the current user isn't root, prepend the command with `sudo`.
    """
    if os.geteuid() != 0:               # type: ignore
        args = ['sudo'] + args

    return Popen(args, **kwargs)

def run_and_print_output(print_func: Callable[[str], None],
                         args: list[str], root: bool = False,
                         send_interrupt: bool = False,
                         **kwargs: Any) -> Popen[Any]:
    """Calls `subprocess.Popen` or `popen_as_root` if `root`
    is `True`, with `args` and `kwargs`.

    Pipes both stdout and stderr, and every time the process writes
    a line to stdout, calls `print_func` with it.

    * If `send_interrupt` is `True`, sends a SIGINT (or CTRL_BREAK_EVENT on Windows)
    to the process when a KeyboardInterrupt occurs. The user will be forced
    to wait for the process to exit.
    """
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.PIPE
    kwargs.setdefault('encoding', 'utf8')

    # On Windows, SIGINT is not supported. We need to create the
    # process in a new process group and send CTRL_BREAK_EVENT to it
    if send_interrupt and os.name == 'nt':
        kwargs.setdefault('creationflags', subprocess.CREATE_NEW_PROCESS_GROUP)
        kwargs['creationflags'] |= subprocess.CREATE_NEW_PROCESS_GROUP

    if root:
        proc = popen_as_root(args, **kwargs)
    else:
        proc = subprocess.Popen(args, **kwargs)

    def read_loop(interrupt_sent: bool):
        try:
            for line in proc.stdout:  # type: ignore
                print_func(line)

            if interrupt_sent:
                # Wait for the process to gracefully exit
                proc.wait()
        except KeyboardInterrupt:
            if interrupt_sent:
                # Force user to wait for the process to
                # gracefully handle the interrupt and exit
                read_loop(True)
                return
            
            # Send interrupt and wait for process to gracefully exit
            if send_interrupt:
                if os.name == 'nt':
                    os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
                else:
                    proc.send_signal(signal.SIGINT)

                read_loop(True)
                proc.wait()
            
            raise KeyboardInterrupt

    try:
        read_loop(False)
        proc.wait()
        return proc
    except KeyboardInterrupt:
        # Wait a little in order to prevent EOFError
        # when user presses CTRL + C
        time.sleep(0.1)
        raise KeyboardInterrupt
    finally:
        proc.terminate()