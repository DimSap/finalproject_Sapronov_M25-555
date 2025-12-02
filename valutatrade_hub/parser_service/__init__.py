"""Parser service package providing configuration and storage helpers."""

from .api_clients import BaseApiClient, CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig, get_parser_config, reload_parser_config
from .storage import (
    append_history_entry,
    ensure_history_store,
    ensure_rates_snapshot,
    load_history,
    load_rates_snapshot,
    save_history,
    save_rates_snapshot,
    upsert_rate_pair,
)
from .updater import RatesUpdater

__all__ = [
    "ParserConfig",
    "get_parser_config",
    "reload_parser_config",
    "BaseApiClient",
    "CoinGeckoClient",
    "ExchangeRateApiClient",
    "RatesUpdater",
    "append_history_entry",
    "ensure_history_store",
    "ensure_rates_snapshot",
    "load_history",
    "load_rates_snapshot",
    "save_history",
    "save_rates_snapshot",
    "upsert_rate_pair",
]

