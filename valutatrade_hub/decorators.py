"""Reusable decorators for domain operations."""

import datetime
import functools
import inspect

from valutatrade_hub.core.currencies import list_supported_codes
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ValutaTradeError,
)
from valutatrade_hub.logging_config import setup_logging

_logger = setup_logging()


def log_action(action, verbose=False):
    """Log action details and outcome."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
            context = {
                'timestamp': timestamp,
                'action': action.upper(),
                'result': 'OK',
            }
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            bound.apply_defaults()
            try:
                result = func(*args, **kwargs)
                context.update(_collect_context(bound.arguments, result, verbose))
                _logger.info(_format_message(context))
                return result
            except Exception as exc:
                context['result'] = 'ERROR'
                context['error_type'] = exc.__class__.__name__
                context['error_message'] = str(exc)
                context.update(_collect_context(bound.arguments, None, verbose))
                _logger.info(_format_message(context))
                raise

        return wrapper

    return decorator


def handle_errors(func):
    """Decorator for CLI handlers to standardise error output."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InsufficientFundsError as error:
            print(error)
        except CurrencyNotFoundError as error:
            print(error)
            codes = ', '.join(sorted(list_supported_codes().keys()))
            print("Подсказка: используйте 'help get-rate' для справки по командам.")
            print(f'Поддерживаемые валюты: {codes}')
        except ApiRequestError as error:
            print(error)
            print('Попробуйте повторить запрос позже или проверьте соединение.')
        except ValutaTradeError as error:
            print(error)
        except ValueError as error:
            print(error)

    return wrapper


def _collect_context(arguments, result, verbose):
    context = {}
    for key in ('user_id', 'username', 'currency_code', 'amount'):
        if key in arguments:
            context[key] = arguments[key]
    if isinstance(result, dict):
        for key in ('user_id', 'username', 'currency_code', 'amount', 'rate', 'base_currency'):
            if key in result:
                context[key] = result[key]
        if verbose:
            for key in ('wallet_before', 'wallet_after', 'base_before', 'base_after'):
                if key in result:
                    context[key] = result[key]
    return context


def _format_message(data):
    parts = []
    log_keys = (
        'timestamp',
        'action',
        'user_id',
        'username',
        'currency_code',
        'amount',
        'rate',
        'base_currency',
        'result',
        'error_type',
        'error_message',
    )
    for key in log_keys:
        if key in data:
            parts.append(f"{key}={data[key]}")
    if 'wallet_before' in data and 'wallet_after' in data:
        parts.append(f"wallet={data['wallet_before']}->{data['wallet_after']}")
    if 'base_before' in data and 'base_after' in data:
        parts.append(f"base={data['base_before']}->{data['base_after']}")
    return ' '.join(parts)


__all__ = ['log_action', 'handle_errors']

