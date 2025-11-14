"""Logging configuration for valutatrade hub."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

_settings = SettingsLoader()
_base_dir = Path(__file__).resolve().parent
_logs_dir = _base_dir / _settings.get('logs_dir')
_logs_dir.mkdir(parents=True, exist_ok=True)


def setup_logging(level=logging.INFO):
    """Configure a simple rotating file handler for action logs."""
    logger = logging.getLogger('valutatrade.actions')
    if logger.handlers:
        return logger

    log_path = _logs_dir / _settings.get('actions_log_file')
    max_bytes = int(_settings.get('log_max_bytes'))
    backup_count = int(_settings.get('log_backup_count'))
    handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)

    log_format = _settings.get('log_format')
    handler.setFormatter(logging.Formatter(log_format))

    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


__all__ = ['setup_logging']

