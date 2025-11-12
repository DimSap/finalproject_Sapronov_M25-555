"""Project-wide constants."""

DEFAULT_RATES = {
    'USD_USD': 1.0,
    'EUR_USD': 1.0786,
    'BTC_USD': 59337.21,
    'RUB_USD': 0.01016,
    'ETH_USD': 3720.0,
}

RATE_FRESH_MINUTES = 5
RATE_SOURCE = 'StubService'

PROMPT_START_MESSAGE = 'Введите команду (help для списка, exit для выхода)'
PROMPT_GOODBYE_MESSAGE = 'До встречи!'
PROMPT_EOF_MESSAGE = '\nВыход.'
SHLEX_ERROR_TEMPLATE = 'Ошибка ввода: {error}'

