"""HTTP clients for external rate providers."""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import requests
from requests.exceptions import RequestException

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import get_parser_config


def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize_timestamp(value):
    """Return ExchangeRate-API timestamps in ISO 8601 UTC form."""
    if not value:
        return _now_iso()
    try:
        parsed = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z")
    except (TypeError, ValueError):
        return _now_iso()
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class BaseApiClient(ABC):
    """Abstract client for fetching exchange rates."""

    def __init__(self, config=None):
        self.config = config or get_parser_config()
        self.name = "base"
        self.source_name = "Base"

    @abstractmethod
    def fetch_rates(self):
        """Return dict with fetched rates."""
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """Fetch cryptocurrency rates from CoinGecko."""

    def __init__(self, config=None):
        super().__init__(config)
        self.name = "coingecko"
        self.source_name = self.config.crypto_source_name

    def fetch_rates(self):
        params = self.config.coingecko_params
        url = self.config.coingecko_url
        start = time.time()
        try:
            response = requests.get(url, params=params, timeout=self.config.request_timeout)
        except RequestException as error:
            raise ApiRequestError(f"CoinGecko недоступен: {error}") from error
        elapsed_ms = int((time.time() - start) * 1000)
        if response.status_code >= 400:
            raise ApiRequestError(f"CoinGecko вернул статус {response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            raise ApiRequestError("CoinGecko: некорректный JSON") from error

        base = self.config.base_currency.upper()
        base_key = base.lower()
        rates = {}
        meta = {}
        for code in self.config.crypto_currencies:
            raw_id = self.config.crypto_id_map.get(code, code.lower())
            entry = payload.get(raw_id) or {}
            value = entry.get(base_key)
            if value is None:
                continue
            pair = f"{code}_{base}"
            rates[pair] = float(value)
            meta[pair] = {
                "raw_id": raw_id,
                "status_code": response.status_code,
                "request_ms": elapsed_ms,
            }
        return {
            "rates": rates,
            "meta": meta,
            "timestamp": _now_iso(),
            "source": self.source_name,
        }


class ExchangeRateApiClient(BaseApiClient):
    """Fetch fiat currency rates from ExchangeRate-API."""

    def __init__(self, config=None):
        super().__init__(config)
        self.name = "exchangerate"
        self.source_name = self.config.fiat_source_name

    def fetch_rates(self):
        url = self.config.exchangerate_url
        start = time.time()
        try:
            response = requests.get(url, timeout=self.config.request_timeout)
        except RequestException as error:
            raise ApiRequestError(f"ExchangeRate-API недоступен: {error}") from error
        elapsed_ms = int((time.time() - start) * 1000)
        if response.status_code >= 400:
            raise ApiRequestError(f"ExchangeRate-API вернул статус {response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            raise ApiRequestError("ExchangeRate-API: некорректный JSON") from error

        if payload.get("result") != "success":
            message = payload.get("error-type") or "неизвестная ошибка"
            raise ApiRequestError(f"ExchangeRate-API сообщил об ошибке: {message}")

        base = self.config.base_currency.upper()
        rates_data = payload["conversion_rates"]
        rates = {}
        meta = {}
        for code in self.config.fiat_currencies:
            value = rates_data.get(code)
            if value is None:
                continue
            pair = f"{code}_{base}"
            rates[pair] = float(value)
            meta[pair] = {
                "raw_id": code,
                "status_code": response.status_code,
                "request_ms": elapsed_ms,
            }
        timestamp = _normalize_timestamp(payload["time_last_update_utc"])
        return {
            "rates": rates,
            "meta": meta,
            "timestamp": timestamp,
            "source": self.source_name,
        }


__all__ = ["BaseApiClient", "CoinGeckoClient", "ExchangeRateApiClient"]


