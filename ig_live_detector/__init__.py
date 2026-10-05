"""ig-live-detector: pure-Python Instagram Live detector (FBNS push) with optional webhook / recording outputs."""
from ._version import __version__
from .api import make_register_token, record_lives, run_detector, watch_lives
from .webhook import make_webhook_notifier

__all__ = [
    "watch_lives",
    "run_detector",
    "record_lives",
    "make_register_token",
    "make_webhook_notifier",
    "__version__",
]
