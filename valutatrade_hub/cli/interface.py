from valutatrade_hub.core import usecases

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


def handle_register(args):
    """Process user registration command."""
    username = args.username.strip()
    result = usecases.register_user(username, args.password)
    print(
        f"Пользователь '{result['username']}' зарегистрирован (id={result['user_id']}). "
        f"Войдите: login --username {result['username']} --password ****"
    )


def handle_login(args):
    """Process user login command."""
    username = args.username.strip()
    result = usecases.login_user(username, args.password)
    SESSION['user'] = result
    print(f"Вы вошли как '{result['username']}'")


def handle_show_portfolio(args):
    """Display wallet balances for the active user."""
    user = require_login()
    base_currency = args.base.upper() if args.base else 'USD'
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


def handle_buy(args):
    """Execute currency purchase for the active user."""
    user = require_login()
    currency = args.currency.upper()
    result = usecases.buy_currency(user['user_id'], currency, args.amount)
    print(
        f"Покупка выполнена: {format_balance(result['amount'], currency)} {currency} "
        f"по курсу {format_money(result['rate'])} USD/{currency}"
    )
    print('Изменения в портфеле:')
    print(
        f"- {currency}: было {format_balance(result['wallet_before'], currency)} → "
        f"стало {format_balance(result['wallet_after'], currency)}"
    )
    print(
        f"- USD: было {format_money(result['usd_before'])} → стало {format_money(result['usd_after'])}"
    )
    print(f"Оценочная стоимость покупки: {format_money(result['cost'])} USD")


def handle_sell(args):
    """Execute currency sale for the active user."""
    user = require_login()
    currency = args.currency.upper()
    result = usecases.sell_currency(user['user_id'], currency, args.amount)
    print(
        f"Продажа выполнена: {format_balance(result['amount'], currency)} {currency} "
        f"по курсу {format_money(result['rate'])} USD/{currency}"
    )
    print('Изменения в портфеле:')
    print(
        f"- {currency}: было {format_balance(result['wallet_before'], currency)} → "
        f"стало {format_balance(result['wallet_after'], currency)}"
    )
    print(
        f"- USD: было {format_money(result['usd_before'])} → стало {format_money(result['usd_after'])}"
    )
    print(f"Оценочная выручка: {format_money(result['revenue'])} USD")


def handle_get_rate(args):
    """Display current exchange rate for the pair."""
    from_currency = args.from_currency.upper()
    to_currency = args.to_currency.upper()
    result = usecases.fetch_rate(from_currency, to_currency)
    print(
        f"Курс {result['from']}→{result['to']}: {result['rate']:.8f} (обновлено: {result['updated_at']})"
    )
    if result['inverse'] is not None:
        print(f"Обратный курс {result['to']}→{result['from']}: {result['inverse']:.8f}")


COMMAND_HANDLERS = {
    'register': handle_register,
    'login': handle_login,
    'show-portfolio': handle_show_portfolio,
    'buy': handle_buy,
    'sell': handle_sell,
    'get-rate': handle_get_rate,
}
