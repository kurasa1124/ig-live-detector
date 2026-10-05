"""ig-live-detector: pure-Python Instagram Live detection via FBNS push + auto recorder."""
from ._version import __version__
from .api import make_register_token, record_lives, watch_lives

__all__ = ["watch_lives", "record_lives", "make_register_token", "__version__"]
