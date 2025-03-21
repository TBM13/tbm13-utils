import os
import subprocess
import time

from typing import Callable

__all__ = [
    'get_unique_file',
    'run_as_root', 'popen_as_root', 'run_and_print_output'
]

def get_unique_file(file_path: str) -> str:
    """Generates an unique file name for `file_path` and returns it.
    
    If `file_path` does not exist, returns it as-is.
    Otherwise, appends a number to it.
    """

    base_name = os.path.basename(file_path)
    extension = ''
    if '.' in base_name:
        # Make sure file_path is not something like ".gitignore"
        if len(base_name.split('.')[0]) > 0:
            extension = file_path[file_path.rfind('.'):]
            file_path = file_path[:file_path.rfind(extension)]

    unique_path = file_path + extension

    i = 1
    while os.path.exists(unique_path):
        unique_path = f"{file_path}_{i}{extension}"
        i += 1
    
    return unique_path

def run_as_root(args, **kwargs) -> subprocess.CompletedProcess:
    """Calls `subprocess.run` with `args` and `kwargs`.
    
    If the current user isn't root, prepend the command with `sudo`.
    """
    if os.geteuid() != 0:
        args = ['sudo'] + list(args)

    return subprocess.run(args, **kwargs)

def popen_as_root(args, **kwargs) -> subprocess.Popen:
    """Calls `subprocess.Popen` with `args` and `kwargs`.
    
    If the current user isn't root, prepend the command with `sudo`.
    """
    if os.geteuid() != 0:
        args = ['sudo'] + list(args)

    return subprocess.Popen(args, **kwargs)

def run_and_print_output(print_func: Callable[[str], None],
                         args, root: bool = False,
                         **kwargs) -> subprocess.Popen:
    """Calls `subprocess.Popen` or `popen_as_root` if `root`
    is `True`, with `args` and `kwargs`.
    
    Pipes both stdout and stderr, and every time the process writes
    a line to stdout, calls `print_func` with it.
    """

    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    kwargs.setdefault('encoding', 'utf8')

    if root:
        proc = popen_as_root(args, **kwargs)
    else:
        proc = subprocess.Popen(args, **kwargs)

    try:
        while 1:
            line = proc.stdout.readline()
            if not line: 
                if proc.poll() is not None:
                    break

                proc.wait()
                continue

            print_func(line)

        return proc
    except KeyboardInterrupt:
        # Wait a little in order to prevent EOFError
        # when user presses CTRL + C
        time.sleep(0.1)
        raise KeyboardInterrupt
    finally:
        proc.terminate()