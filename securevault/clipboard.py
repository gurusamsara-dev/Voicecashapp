"""
clipboard.py — Secure clipboard handling with automatic clear timer.

Uses pyperclip for cross-platform clipboard access.
Launches a daemon thread that clears the clipboard after a configurable delay.
"""

import threading
import time
import logging

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYPERCLIP_AVAILABLE = False

logger = logging.getLogger(__name__)

# Seconds before the clipboard is automatically cleared
DEFAULT_CLEAR_DELAY: int = 12

# Module-level reference to the active clear timer so we can cancel it when
# the user copies a new item before the previous timer fires.
_active_timer: threading.Timer | None = None
_timer_lock = threading.Lock()


def _clear_clipboard(on_cleared=None) -> None:
    """Internal: overwrite clipboard with an empty string and fire *on_cleared*."""
    try:
        if _PYPERCLIP_AVAILABLE:
            pyperclip.copy("")
        logger.debug("Clipboard cleared.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not clear clipboard: %s", exc)
    finally:
        if callable(on_cleared):
            try:
                on_cleared()
            except Exception:  # noqa: BLE001
                pass


def copy_to_clipboard(
    text: str,
    delay: int = DEFAULT_CLEAR_DELAY,
    on_copied=None,
    on_cleared=None,
) -> bool:
    """Copy *text* to the system clipboard and schedule an automatic clear.

    Parameters
    ----------
    text:
        The plaintext string to copy (typically a decrypted secret).
    delay:
        Seconds to wait before clearing the clipboard (default 12).
    on_copied:
        Optional zero-argument callable invoked immediately after the copy.
    on_cleared:
        Optional zero-argument callable invoked after the clipboard is cleared.

    Returns
    -------
    bool
        ``True`` on success, ``False`` if pyperclip is unavailable or an error
        occurred.
    """
    global _active_timer

    if not _PYPERCLIP_AVAILABLE:
        logger.error("pyperclip is not installed; cannot copy to clipboard.")
        return False

    try:
        pyperclip.copy(text)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to copy to clipboard: %s", exc)
        return False

    # Cancel any previously scheduled clear
    with _timer_lock:
        if _active_timer is not None:
            _active_timer.cancel()

        timer = threading.Timer(delay, _clear_clipboard, kwargs={"on_cleared": on_cleared})
        timer.daemon = True
        timer.start()
        _active_timer = timer

    logger.debug("Copied to clipboard; will clear in %d seconds.", delay)

    if callable(on_copied):
        try:
            on_copied()
        except Exception:  # noqa: BLE001
            pass

    return True


def cancel_clear_timer() -> None:
    """Cancel the active clipboard clear timer without clearing the clipboard."""
    global _active_timer
    with _timer_lock:
        if _active_timer is not None:
            _active_timer.cancel()
            _active_timer = None
