import gc
import logging
import os
import ctypes

logger = logging.getLogger(__name__)


def trim_memory():
    """
    Force Python garbage collection and request the OS to reclaim freed heap pages.
    Supports Windows working set reduction and Linux malloc_trim.
    """
    # 1. Force Python garbage collection
    collected = gc.collect()
    logger.debug(f"Garbage collector: freed {collected} objects.")

    # 2. OS-level working set trim
    if os.name == 'nt':
        try:
            # Windows API: SetProcessWorkingSetSize(handle, -1, -1) flushes unused pages
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
            logger.debug("Windows working set trimmed successfully.")
        except Exception as e:
            logger.debug(f"Windows memory trim error: {e}")
    else:
        try:
            # Linux glibc malloc_trim
            ctypes.CDLL('libc.so.6').malloc_trim(0)
            logger.debug("Linux malloc_trim executed successfully.")
        except Exception:
            pass
