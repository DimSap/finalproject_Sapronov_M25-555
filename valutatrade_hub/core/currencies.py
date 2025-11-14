"""Currency hierarchy and registry."""

import re
from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError

CODE_PATTERN = re.compile(r'^[A-Z]{2,5}$')


class Currency(ABC):
    """Abstract base class describing a currency entity."""

    __slots__ = ('_name', '_code')

    def __init__(self, name, code):
        self._name = self._validate_name(name)
        self._code = self._validate_code(code)

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Currency name must be a non-empty string')
        return name.strip()

    @staticmethod
    def _validate_code(code):
        if not isinstance(code, str):
            raise ValueError('Currency code must be a string')
        code = code.strip().upper()
        if not CODE_PATTERN.match(code):
            raise ValueError('Currency code must be 2-5 uppercase letters')
        return code

    @property
    def name(self):
        return self._name

    @property
    def code(self):
        return self._code

    @abstractmethod
    def get_display_info(self):
        """Return a human-readable representation."""


class FiatCurrency(Currency):
    """Currency issued by a sovereign entity."""

    __slots__ = ('_issuing_country',)

    def __init__(self, name, code, issuing_country):
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError('Issuing country must be provided')
        self._issuing_country = issuing_country.strip()

    @property
    def issuing_country(self):
        return self._issuing_country

    def get_display_info(self):
        return f'[FIAT] {self.code} - {self.name} (Issuing: {self.issuing_country})'


class CryptoCurrency(Currency):
    """Currency based on cryptographic consensus."""

    __slots__ = ('_algorithm', '_market_cap')

    def __init__(self, name, code, algorithm, market_cap):
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError('Algorithm must be provided')
        if not isinstance(market_cap, (int, float)) or market_cap < 0:
            raise ValueError('Market cap must be a non-negative number')
        self._algorithm = algorithm.strip()
        self._market_cap = float(market_cap)

    @property
    def algorithm(self):
        return self._algorithm

    @property
    def market_cap(self):
        return self._market_cap

    def get_display_info(self):
        formatted_cap = f'{self.market_cap:.2e}'.replace('e+', 'e')
        return f'[CRYPTO] {self.code} - {self.name} (Algo: {self.algorithm}, MCAP: {formatted_cap})'


_CURRENCY_REGISTRY = {}


def _register_currency(currency):
    _CURRENCY_REGISTRY[currency.code] = currency


_register_currency(FiatCurrency('US Dollar', 'USD', 'United States'))
_register_currency(FiatCurrency('Euro', 'EUR', 'Eurozone'))
_register_currency(FiatCurrency('Russian Ruble', 'RUB', 'Russian Federation'))
_register_currency(CryptoCurrency('Bitcoin', 'BTC', 'SHA-256', 1.12e12))
_register_currency(CryptoCurrency('Ethereum', 'ETH', 'Ethash', 4.80e11))


def get_currency(code):
    """Return a currency from the registry by code."""
    if not isinstance(code, str) or not code.strip():
        raise CurrencyNotFoundError(code or '<empty>')
    normalized = code.strip().upper()
    currency = _CURRENCY_REGISTRY.get(normalized)
    if not currency:
        raise CurrencyNotFoundError(normalized)
    return currency


def list_supported_codes():
    """Return a copy of the currency registry."""
    return dict(_CURRENCY_REGISTRY)


__all__ = [
    'Currency',
    'FiatCurrency',
    'CryptoCurrency',
    'get_currency',
    'list_supported_codes',
]

