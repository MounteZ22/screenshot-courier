"""Prevent Windows from sleeping / turning off the display."""

import ctypes
import logging

logger = logging.getLogger(__name__)

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def keep_awake_on():
    """Prevent screen-off and system sleep while the app runs."""
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )
    logger.info("Screen sleep prevention enabled")


def keep_awake_off():
    """Restore default Windows power policy."""
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    logger.info("Screen sleep prevention disabled")
