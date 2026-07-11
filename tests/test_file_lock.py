"""测试 file_lock 模块"""

import threading
import time
from pathlib import Path
from engine.file_lock import file_lock, FileLockError


class TestFileLock:
    def test_acquire_and_release_lock(self, tmp_path):
        lock_path = tmp_path / "test.lock"
        with file_lock(lock_path, timeout=1.0):
            assert lock_path.exists()
        # 锁释放后，另一个进程可以获取

    def test_lock_prevents_concurrent_access(self, tmp_path):
        lock_path = tmp_path / "concurrent.lock"
        results = []
        barrier = threading.Barrier(2)

        def worker(worker_id):
            if worker_id == 1:
                with file_lock(lock_path, timeout=1.0):
                    results.append(f"enter-{worker_id}")
                    barrier.wait()  # signal thread 2 that lock is held
                    time.sleep(0.5)
                    results.append(f"exit-{worker_id}")
            else:
                barrier.wait()  # wait until thread 1 holds the lock
                try:
                    with file_lock(lock_path, timeout=0.2):
                        results.append(f"enter-{worker_id}")
                        results.append(f"exit-{worker_id}")
                except FileLockError:
                    results.append(f"timeout-{worker_id}")

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 第二个线程应该超时，因为锁被第一个占用
        assert "timeout-2" in results

    def test_lock_with_context_manager_auto_releases(self, tmp_path):
        lock_path = tmp_path / "auto.lock"
        with file_lock(lock_path):
            pass
        # 锁应自动释放
        with file_lock(lock_path, timeout=0.1):
            pass  # 如果能获取，说明已释放

    def test_creates_parent_directory(self, tmp_path):
        lock_path = tmp_path / "sub" / "dir" / "nested.lock"
        with file_lock(lock_path):
            assert lock_path.parent.exists()
