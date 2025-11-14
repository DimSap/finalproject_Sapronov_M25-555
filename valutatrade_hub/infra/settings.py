"""Application configuration loader implemented as a Singleton."""

import json
from pathlib import Path
from threading import Lock

DEFAULT_CONFIG = {
    'data_dir': 'data',
    'users_file': 'data/users.json',
    'portfolios_file': 'data/portfolios.json',
    'rates_file': 'data/rates.json',
    'rates_ttl_seconds': 300,
    'default_base_currency': 'USD',
    'logs_dir': 'logs',
    'log_file': 'logs/app.log',
    'log_format': '[%(levelname)s] %(asctime)s %(name)s: %(message)s',
}


class SettingsLoader:
    """Read-only access to project configuration values."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        # Using __new__ keeps the implementation compact and easy to follow
        # without introducing a metaclass, while still guaranteeing a singleton.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._base_dir = Path(__file__).resolve().parent.parent.parent
        self._config_path = self._base_dir / 'config.json'
        self._data = {}
        self.reload()
        self._initialized = True

    def _ensure_config_file(self):
        if self._config_path.exists():
            return
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with self._config_path.open('w', encoding='utf-8') as fh:
            json.dump(DEFAULT_CONFIG, fh, ensure_ascii=False, indent=2)

    def reload(self):
        """Reload configuration from disk."""
        self._ensure_config_file()
        with self._config_path.open('r', encoding='utf-8') as fh:
            self._data = json.load(fh)

    def get(self, key, default=None):
        """Return a configuration value."""
        return self._data.get(key, default)

    @property
    def config_path(self):
        """Return an absolute path to the config file."""
        return self._config_path


__all__ = ['SettingsLoader']

