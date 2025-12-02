"""Configuration helpers for the parser service."""

import json
import os
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_settings = SettingsLoader()

DEFAULT_PARSER_SETTINGS = {
    "coingecko_url": "https://api.coingecko.com/api/v3/simple/price",
    "exchangerate_api_url": "https://v6.exchangerate-api.com/v6",
    "base_currency": "USD",
    "fiat_currencies": ["EUR", "GBP", "RUB"],
    "crypto_currencies": ["BTC", "ETH", "SOL"],
    "crypto_id_map": {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"},
    "request_timeout": 10,
    "crypto_source_name": "CoinGecko",
    "fiat_source_name": "ExchangeRate-API",
}


def _env(name, default=""):
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _env_list(name):
    raw = _env(name)
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_mapping(name):
    raw = _env(name)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _normalize_codes(codes):
    normalized = []
    for code in codes or []:
        text = str(code).strip()
        if text:
            normalized.append(text.upper())
    return tuple(normalized)


def _normalize_crypto_map(mapping, codes):
    table = {}
    for key, value in (mapping or {}).items():
        if not value:
            continue
        table[str(key).upper()] = str(value).strip()
    for code in codes:
        table.setdefault(code, code.lower())
    return table


def _path_from_config(key, default):
    location = _settings.get(key, default)
    return BASE_DIR / location


def _build_parser_options():
    coingecko_url = _env(
        "PARSER_COINGECKO_URL",
        _settings.get("parser_coingecko_url", DEFAULT_PARSER_SETTINGS["coingecko_url"]),
    )
    exchangerate_api_url = _env(
        "PARSER_EXCHANGERATE_API_URL",
        _settings.get("parser_exchangerate_api_url", DEFAULT_PARSER_SETTINGS["exchangerate_api_url"]),
    )
    base_currency = (
        _env("PARSER_BASE_CURRENCY", _settings.get("parser_base_currency", DEFAULT_PARSER_SETTINGS["base_currency"]))
        .strip()
        .upper()
        or DEFAULT_PARSER_SETTINGS["base_currency"]
    )

    fiat_codes = _env_list("PARSER_FIAT_CODES")
    if not fiat_codes:
        fiat_codes = _settings.get("parser_fiat_currencies", DEFAULT_PARSER_SETTINGS["fiat_currencies"])
    fiat_codes = _normalize_codes(fiat_codes)

    crypto_codes = _env_list("PARSER_CRYPTO_CODES")
    if not crypto_codes:
        crypto_codes = _settings.get("parser_crypto_currencies", DEFAULT_PARSER_SETTINGS["crypto_currencies"])
    crypto_codes = _normalize_codes(crypto_codes)

    crypto_map = _env_mapping("PARSER_CRYPTO_ID_MAP")
    if not crypto_map:
        crypto_map = _settings.get("parser_crypto_id_map", DEFAULT_PARSER_SETTINGS["crypto_id_map"])
    crypto_map = _normalize_crypto_map(crypto_map, crypto_codes)

    timeout_value = _env(
        "PARSER_REQUEST_TIMEOUT",
        _settings.get("parser_request_timeout", DEFAULT_PARSER_SETTINGS["request_timeout"]),
    )
    try:
        request_timeout = int(timeout_value)
    except (TypeError, ValueError):
        request_timeout = DEFAULT_PARSER_SETTINGS["request_timeout"]

    crypto_source_name = _env(
        "PARSER_CRYPTO_SOURCE_NAME",
        _settings.get("parser_crypto_source_name", DEFAULT_PARSER_SETTINGS["crypto_source_name"]),
    )
    fiat_source_name = _env(
        "PARSER_FIAT_SOURCE_NAME",
        _settings.get("parser_fiat_source_name", DEFAULT_PARSER_SETTINGS["fiat_source_name"]),
    )

    return {
        "exchange_rate_api_key": _env("EXCHANGERATE_API_KEY"),
        "coingecko_url": coingecko_url,
        "exchangerate_api_url": exchangerate_api_url,
        "base_currency": base_currency,
        "fiat_currencies": fiat_codes,
        "crypto_currencies": crypto_codes,
        "crypto_id_map": crypto_map,
        "request_timeout": request_timeout,
        "crypto_source_name": crypto_source_name,
        "fiat_source_name": fiat_source_name,
        "rates_file_path": _path_from_config("rates_file", "data/rates.json"),
        "history_file_path": _path_from_config("rates_history_file", "data/exchange_rates.json"),
    }


class ParserConfig:
    """Store parser settings for API access and file paths."""

    def __init__(self, options):
        self.exchange_rate_api_key = options["exchange_rate_api_key"]
        self.coingecko_url = options["coingecko_url"]
        self.exchangerate_api_url = options["exchangerate_api_url"]
        self.base_currency = options["base_currency"]
        self.fiat_currencies = options["fiat_currencies"]
        self.crypto_currencies = options["crypto_currencies"]
        self.crypto_id_map = options["crypto_id_map"]
        self.request_timeout = options["request_timeout"]
        self.crypto_source_name = options["crypto_source_name"]
        self.fiat_source_name = options["fiat_source_name"]
        self.rates_file_path = options["rates_file_path"]
        self.history_file_path = options["history_file_path"]

    @property
    def coingecko_params(self):
        ids = [self.crypto_id_map.get(code, code.lower()) for code in self.crypto_currencies]
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
        _CONFIG = ParserConfig(_build_parser_options())
    return _CONFIG


def reload_parser_config():
    global _CONFIG
    _CONFIG = ParserConfig(_build_parser_options())
    return _CONFIG


__all__ = ["ParserConfig", "get_parser_config", "reload_parser_config"]
