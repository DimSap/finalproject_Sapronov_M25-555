from valutatrade_hub.core import usecases
from valutatrade_hub.core.utils import load_rates
from valutatrade_hub.decorators import handle_errors
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import CoinGeckoClient, ExchangeRateApiClient
from valutatrade_hub.parser_service.config import get_parser_config
from valutatrade_hub.parser_service.updater import RatesUpdater

_settings = SettingsLoader()
BASE_CURRENCY_CODE = (_settings.get('default_base_currency') or 'USD').strip().upper()

SESSION = {'user': None}


def format_balance(value, currency):
    """Format balance with currency-specific precision."""
    if currency == 'USD':
        return f'{value:.2f}'
    return f'{value:.4f}'


def format_money(value):
    """Format monetary value with two decimals."""
    return f'{value:.2f}'


def require_login():
    """Ensure there is an active user session."""
    user = SESSION.get('user')
    if not user:
        raise ValueError('Сначала выполните login')
    return user


@handle_errors
def handle_register(args):
    """Process user registration command."""
    username = args.username.strip()
    result = usecases.register_user(username, args.password)
    print(
        f"Пользователь '{result['username']}' зарегистрирован (id={result['user_id']}). "
        f"Войдите: login --username {result['username']} --password ****"
    )


@handle_errors
def handle_login(args):
    """Process user login command."""
    username = args.username.strip()
    result = usecases.login_user(username, args.password)
    SESSION['user'] = result
    print(f"Вы вошли как '{result['username']}'")


@handle_errors
def handle_show_portfolio(args):
    """Display wallet balances for the active user."""
    user = require_login()
    base_currency = args.base.strip().upper() if args.base else BASE_CURRENCY_CODE
    overview = usecases.get_portfolio_overview(user['user_id'], base_currency)

    wallets = overview['wallets']
    if not wallets:
        print(f"Портфель пользователя '{user['username']}' пуст")
        return

    print(f"Портфель пользователя '{user['username']}' (база: {overview['base_currency']}):")
    for item in wallets:
        balance_text = format_balance(item['balance'], item['currency_code'])
        converted_text = format_money(item['converted'])
        print(f"- {item['currency_code']}: {balance_text}  → {converted_text} {overview['base_currency']}")
    print('---------------------------------')
    print(f"ИТОГО: {format_money(overview['total'])} {overview['base_currency']}")


@handle_errors
def handle_buy(args):
    """Execute currency purchase for the active user."""
    user = require_login()
    currency = args.currency.strip().upper()
    result = usecases.buy_currency(user['user_id'], currency, args.amount)
    base_currency = result.get('base_currency', BASE_CURRENCY_CODE)
    print(
        f"Покупка выполнена: {format_balance(result['amount'], currency)} {currency} "
        f"по курсу {format_money(result['rate'])} {base_currency}/{currency}"
    )
    print('Изменения в портфеле:')
    print(
        f"- {currency}: было {format_balance(result['wallet_before'], currency)} → "
        f"стало {format_balance(result['wallet_after'], currency)}"
    )
    print(
        f"- {base_currency}: было {format_money(result['base_before'])} → "
        f"стало {format_money(result['base_after'])}"
    )
    print(f"Оценочная стоимость покупки: {format_money(result['cost'])} {base_currency}")


@handle_errors
def handle_sell(args):
    """Execute currency sale for the active user."""
    user = require_login()
    currency = args.currency.strip().upper()
    result = usecases.sell_currency(user['user_id'], currency, args.amount)
    base_currency = result.get('base_currency', BASE_CURRENCY_CODE)
    print(
        f"Продажа выполнена: {format_balance(result['amount'], currency)} {currency} "
        f"по курсу {format_money(result['rate'])} {base_currency}/{currency}"
    )
    print('Изменения в портфеле:')
    print(
        f"- {currency}: было {format_balance(result['wallet_before'], currency)} → "
        f"стало {format_balance(result['wallet_after'], currency)}"
    )
    if currency != base_currency:
        print(
            f"- {base_currency}: было {format_money(result['base_before'])} → "
            f"стало {format_money(result['base_after'])}"
        )
        print(f"Оценочная выручка: {format_money(result['revenue'])} {base_currency}")


@handle_errors
def handle_get_rate(args):
    """Display current exchange rate for the pair."""
    from_currency = args.from_currency.strip().upper()
    to_currency = args.to_currency.strip().upper()
    result = usecases.fetch_rate(from_currency, to_currency)
    print(
        f"Курс {result['from']}→{result['to']}: {result['rate']:.8f} (обновлено: {result['updated_at']})"
    )
    if result['inverse'] is not None:
        print(f"Обратный курс {result['to']}→{result['from']}: {result['inverse']:.8f}")


@handle_errors
def handle_update_rates(args):
    """Fetch fresh rates from external APIs."""
    config = get_parser_config()
    source = args.source.strip().lower() if getattr(args, 'source', None) else None
    all_clients = {
        'coingecko': CoinGeckoClient(config),
        'exchangerate': ExchangeRateApiClient(config),
    }
    if source:
        if source not in all_clients:
            raise ValueError(f"Неизвестный источник '{source}'. Доступны: coingecko, exchangerate.")
        clients = [all_clients[source]]
    else:
        clients = list(all_clients.values())

    updater = RatesUpdater(clients)
    print('INFO: Запуск обновления курсов...')
    result = updater.run_update()
    details = result.get('details') or []
    for detail in details:
        if detail.get('status') == 'ok':
            count = detail.get('count', 0)
            print(f"INFO: {detail['source']} — OK ({count} курсов)")
        else:
            message = detail.get('message', 'ошибка')
            print(f"ERROR: {detail['source']} — {message}")

    if result['errors']:
        print("Обновление завершено с ошибками. Проверьте журнал действий.")
    else:
        print('Обновление выполнено успешно.')

    last_refresh = result.get('last_refresh') or 'неизвестно'
    print(f"Всего обновлено: {result['updated_count']}. Последнее обновление: {last_refresh}")


@handle_errors
def handle_show_rates(args):
    """Display cached exchange rates with optional filters."""
    data = load_rates()
    pairs = data.get('pairs') or {}
    if not pairs:
        print("Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные.")
        return

    currency_filter = args.currency.strip().upper() if getattr(args, 'currency', None) else None
    base_filter = args.base.strip().upper() if getattr(args, 'base', None) else None
    items = []
    for pair, entry in pairs.items():
        if not isinstance(entry, dict):
            continue
        if '_' not in pair:
            continue
        from_code, to_code = pair.split('_', 1)
        rate = entry.get('rate')
        updated_at = entry.get('updated_at')
        source = entry.get('source') or data.get('source') or 'Unknown'
        if currency_filter and currency_filter not in (from_code, to_code):
            continue
        if base_filter and to_code != base_filter:
            continue
        items.append(
            {
                'pair': pair,
                'from': from_code,
                'to': to_code,
                'rate': rate,
                'updated_at': updated_at,
                'source': source,
            }
        )

    if not items:
        if currency_filter:
            print(f"Курс для '{currency_filter}' не найден в кеше.")
        else:
            print('Подходящих записей не найдено.')
        return

    if getattr(args, 'top', None):
        items.sort(key=lambda item: item['rate'] if item['rate'] is not None else 0, reverse=True)
        items = items[: args.top]
    else:
        items.sort(key=lambda item: item['pair'])

    header_refresh = data.get('last_refresh') or items[0]['updated_at'] or 'неизвестно'
    print(f"Курсы из кеша (обновлено: {header_refresh}):")
    for item in items:
        rate = item['rate']
        if rate is None:
            continue
        if rate >= 100:
            rate_text = f"{rate:.2f}"
        elif rate >= 1:
            rate_text = f"{rate:.4f}"
        else:
            rate_text = f"{rate:.6f}"
        updated_at = item['updated_at'] or header_refresh
        print(f"- {item['pair']}: {rate_text} (источник: {item['source']}, обновлено: {updated_at})")


COMMAND_HANDLERS = {
    'register': handle_register,
    'login': handle_login,
    'show-portfolio': handle_show_portfolio,
    'buy': handle_buy,
    'sell': handle_sell,
    'get-rate': handle_get_rate,
    'update-rates': handle_update_rates,
    'show-rates': handle_show_rates,
}
