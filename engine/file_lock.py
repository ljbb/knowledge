"""跨平台文件锁 — 防止并发写入冲突"""

import os
import time
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class FileLockError(Exception):
    """文件锁错误。"""
    pass


@contextmanager
def file_lock(lock_path: Path, timeout: float = 10.0):
    """跨平台文件锁上下文管理器。

    Args:
        lock_path: 锁文件路径
        timeout: 获取锁的超时时间（秒）

    Yields:
        None

    Raises:
        FileLockError: 超时未获取到锁
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(str(lock_path), "a")

    # Windows msvcrt byte-range locks require the file to have at least
    # one byte to lock against; write a sentinel byte and seek back.
    # Using "a" (append) mode avoids truncation that can invalidate locks
    # held by other handles pointing at the same file.
    if os.name == "nt":
        lock_file.write("\n")
        lock_file.flush()
        lock_file.seek(0)

    start = time.monotonic()
    acquired = False

    try:
        while time.monotonic() - start < timeout:
            try:
                if os.name == "nt":
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (IOError, OSError):
                time.sleep(0.1)

        if not acquired:
            raise FileLockError(
                f"无法在 {timeout}s 内获取文件锁: {lock_path}"
            )

        yield

    finally:
        if acquired:
            try:
                if os.name == "nt":
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass
        lock_file.close()
