"""Configuration helpers for the parser service."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _env(key, default=""):
    value = os.getenv(key, default)
    if value is None:
        return default
    return value.strip()


class ParserConfig:
    """Store parser settings for API access and file paths."""

    def __init__(self, exchange_rate_api_key):
        self.exchange_rate_api_key = exchange_rate_api_key
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        self.exchangerate_api_url = "https://v6.exchangerate-api.com/v6"
        self.base_currency = "USD"
        self.fiat_currencies = tuple(code.upper() for code in ("EUR", "GBP", "RUB"))
        self.crypto_currencies = tuple(code.upper() for code in ("BTC", "ETH", "SOL"))
        self.crypto_id_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
        self.rates_file_path = BASE_DIR / "data" / "rates.json"
        self.history_file_path = BASE_DIR / "data" / "exchange_rates.json"
        self.request_timeout = 10
        self.crypto_source_name = "CoinGecko"
        self.fiat_source_name = "ExchangeRate-API"

    @property
    def coingecko_params(self):
        ids = []
        for code in self.crypto_currencies:
            ids.append(self.crypto_id_map.get(code, code.lower()))
        return {
            "ids": ",".join(ids),
            "vs_currencies": self.base_currency.lower(),
        }

    @property
    def exchangerate_url(self):
        return f"{self.exchangerate_api_url}/{self.exchange_rate_api_key}/latest/{self.base_currency}"


_CONFIG = None


def get_parser_config():
    global _CONFIG
    if _CONFIG is None:
        key = _env("EXCHANGERATE_API_KEY")
        _CONFIG = ParserConfig(key)
    return _CONFIG


def reload_parser_config():
    global _CONFIG
    key = _env("EXCHANGERATE_API_KEY")
    _CONFIG = ParserConfig(key)
    return _CONFIG


__all__ = ["ParserConfig", "get_parser_config", "reload_parser_config"]

