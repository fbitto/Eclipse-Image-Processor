"""Fine-grained progress from deep numerical code to whoever is listening.

Operators call ``report(done, total, detail)`` between their own steps (scales,
tiles, rings). The call costs one context-variable lookup and does nothing
unless a listener was installed with ``progress_scope``; the task registry does
that for each layer. Thread pools that run work through ``copy_context`` inherit
the listener, exactly like the cancellation token in ``core.cancellation``.
"""
from contextlib import contextmanager
from contextvars import ContextVar

_listener = ContextVar('progress_listener', default=None)


def report(done, total, detail=''):
    """Announce that ``done`` of ``total`` steps of the current task are finished."""
    listener = _listener.get()
    if listener is not None:
        listener(done, total, detail)


@contextmanager
def progress_scope(listener):
    """Send ``report`` calls made inside this block (and its helper threads) to ``listener``."""
    token = _listener.set(listener)
    try:
        yield
    finally:
        _listener.reset(token)
