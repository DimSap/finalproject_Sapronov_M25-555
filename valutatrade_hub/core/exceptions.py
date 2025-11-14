"""Domain-specific exceptions for the valutatrade hub package."""


class ValutaTradeError(Exception):
    """Base class for project-specific errors."""


class InsufficientFundsError(ValutaTradeError):
    """Raised when a wallet lacks enough balance for an operation."""

    def __init__(self, available, required, code):
        if required <= 0:
            raise ValueError('required amount must be positive')
        if available < 0:
            raise ValueError('available amount cannot be negative')
        if not isinstance(code, str) or not code:
            raise ValueError('currency code must be provided')
        self.available = available
        self.required = required
        self.code = code
        message = (
            f'Недостаточно средств: доступно {available:.4f} {code}, '
            f'требуется {required:.4f} {code}'
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Raised when requested currency is not registered or supported."""

    def __init__(self, code):
        if not code:
            raise ValueError('code must be provided')
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Raised when external API interaction fails."""

    def __init__(self, reason):
        if not reason:
            raise ValueError('reason must be provided')
        self.reason = reason
        super().__init__(f'Ошибка при обращении к внешнему API: {reason}')


__all__ = [
    'ValutaTradeError',
    'InsufficientFundsError',
    'CurrencyNotFoundError',
    'ApiRequestError',
]

