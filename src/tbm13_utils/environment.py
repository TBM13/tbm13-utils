import os
import shutil
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from subprocess import CompletedProcess, Popen
from typing import IO, Any, BinaryIO, Literal, TextIO, overload

__all__ = [
    "get_terminal_columns",
    "get_unique_path",
    "open_unique_file",
    "popen_as_root",
    "run_and_print_output",
    "run_as_root",
]


def get_terminal_columns(fallback: int) -> int:
    """Returns the number of columns in the terminal or `fallback`."""
    return shutil.get_terminal_size(fallback=(fallback, 20)).columns


def get_unique_path(path: str | Path) -> Path:
    """Returns a unique path based on `path`.

    It is suggested to use `open_unique_file` when possible
    to avoid TOCTOU issues.
    """
    path = Path(path)
    stem, suffix, parent = path.stem, path.suffix, path.parent

    i = 0
    while True:
        current_path = path if i == 0 else parent / f"{stem}_{i}{suffix}"
        if not current_path.exists():
            return current_path
        i += 1


@overload
def open_unique_file(
    path: str | Path,
    text: Literal[True] = True,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
) -> tuple[TextIO, Path]: ...
@overload
def open_unique_file(
    path: str | Path,
    text: Literal[False],
    buffering: int = -1,
) -> tuple[BinaryIO, Path]: ...
def open_unique_file(
    path: str | Path,
    text: bool = True,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
) -> tuple[IO[str] | IO[bytes], Path]:
    """Atomically creates and opens a file with a unique name based on `path`.

    The file is opened using the exclusive 'x' mode (text) or 'xb' (binary)
    depending on `text`.

    Returns a tuple containing the created file's handle and its path.
    """
    path = Path(path)
    stem, suffix, parent = path.stem, path.suffix, path.parent

    mode = "x" if text else "xb"
    i = 0
    while True:
        current_path = path if i == 0 else parent / f"{stem}_{i}{suffix}"

        try:
            # Atomically check and open the file
            file_handle = current_path.open(
                mode=mode,
                buffering=buffering,
                encoding=encoding,
                errors=errors,
                newline=newline,
            )

            return (file_handle, current_path)
        except FileExistsError:
            i += 1

        run_as_root(["asd"], text=False)


def run_as_root(args: list[str], **kwargs: Any) -> CompletedProcess[Any]:
    """Calls `subprocess.run` with `args` and `kwargs`.

    If the current user isn't root, prepend the command with `sudo`.
    """
    if os.geteuid() != 0:  # type: ignore
        args = ["sudo", *args]

    return subprocess.run(args, **kwargs)  # type: ignore  # noqa: PLW1510


def popen_as_root(args: list[str], **kwargs: Any) -> Popen[Any]:
    """Calls `subprocess.Popen` with `args` and `kwargs`.

    If the current user isn't root, prepend the command with `sudo`.
    """
    if os.geteuid() != 0:  # type: ignore
        args = ["sudo", *args]

    return Popen(args, **kwargs)


def run_and_print_output(
    print_func: Callable[[str], None],
    args: list[str],
    root: bool = False,
    send_interrupt: bool = False,
    **kwargs: Any,
) -> Popen[str]:
    """Calls `subprocess.Popen` with the given args and kwargs.

    Pipes both stdout and stderr, calling `print_func` for each
    line the process outputs.

    * When `send_interrupt` is `True`, sends SIGINT (or CTRL_BREAK_EVENT on Windows)
    to the process when a KeyboardInterrupt occurs. The user will be forced
    to wait for the process to exit.
    """
    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.STDOUT
    kwargs.setdefault("encoding", "utf8")

    # On Windows, SIGINT is not supported. We need to create the
    # process in a new process group and send CTRL_BREAK_EVENT to it
    if send_interrupt and os.name == "nt":
        kwargs["creationflags"] = (
            kwargs.get("creationflags", 0) | subprocess.CREATE_NEW_PROCESS_GROUP
        )

    proc = popen_as_root(args, **kwargs) if root else subprocess.Popen(args, **kwargs)

    interrupt_sent = False
    try:
        while True:
            try:
                if proc.stdout and not proc.stdout.closed:
                    for line in proc.stdout:
                        print_func(line)

                # EOF, wait for the process to exit
                proc.wait()
                break
            except KeyboardInterrupt:
                if not send_interrupt:
                    # Hard cancellation
                    time.sleep(0.1)  # Prevent terminal EOF issues
                    proc.terminate()
                    proc.wait()
                    raise

                if not interrupt_sent:
                    if os.name == "nt":
                        os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
                    else:
                        proc.send_signal(signal.SIGINT)
                    interrupt_sent = True
                else:
                    # Force user to wait for the process to exit
                    continue

        return proc
    except Exception:
        # Clean up process if any unexpected exception occurs
        proc.terminate()
        proc.wait()
        raise
