from .models import Portfolio, User, Wallet
from .utils import (
    current_time_iso,
    find_portfolio,
    find_user,
    generate_salt,
    get_exchange_rate,
    hash_password,
    is_amount_valid,
    is_currency_code,
    load_portfolios,
    load_users,
    next_user_id,
    save_portfolios,
    save_users,
)


def register_user(username, password):
    """Create a new user with an empty portfolio."""
    if not username:
        raise ValueError('Имя пользователя не может быть пустым')
    if len(password) < 4:
        raise ValueError('Пароль должен быть не короче 4 символов')

    users = load_users()
    if find_user(users, username):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = next_user_id(users)
    salt = generate_salt()
    registration_date = current_time_iso()
    user = User(user_id, username, password, salt, registration_date)

    users.append({
        'user_id': user.user_id,
        'username': user.username,
        'hashed_password': user.hashed_password,
        'salt': user.salt,
        'registration_date': registration_date,
    })
    save_users(users)

    portfolios = load_portfolios()
    portfolios.append({
        'user_id': user_id,
        'wallets': {},
    })
    save_portfolios(portfolios)

    return {
        'user_id': user_id,
        'username': username,
    }


def login_user(username, password):
    """Validate credentials and return session data."""
    users = load_users()
    user = find_user(users, username)
    if not user:
        raise ValueError(f"Пользователь '{username}' не найден")

    hashed = hash_password(password, user['salt'])
    if hashed != user['hashed_password']:
        raise ValueError('Неверный пароль')

    return {
        'user_id': user['user_id'],
        'username': user['username'],
    }


def get_portfolio_overview(user_id, base_currency='USD'):
    """Return converted balances for all user wallets."""
    base_currency = base_currency.upper()
    if not is_currency_code(base_currency):
        raise ValueError(f"Неизвестная базовая валюта '{base_currency}'")

    portfolios = load_portfolios()
    record = find_portfolio(portfolios, user_id)
    if not record:
        record = {
            'user_id': user_id,
            'wallets': {},
        }
        portfolios.append(record)
        save_portfolios(portfolios)

    wallets_data = record.get('wallets', {})
    wallets = {}
    for code, data in wallets_data.items():
        wallets[code] = Wallet(code, data.get('balance', 0.0))
    portfolio = Portfolio(user_id, wallets)

    items = []
    total = 0.0
    update_marks = []

    for code, wallet in portfolio.wallets.items():
        rate, updated_at = get_exchange_rate(code, base_currency)
        converted = wallet.balance * rate
        items.append({
            'currency_code': code,
            'balance': wallet.balance,
            'rate': rate,
            'converted': converted,
            'updated_at': updated_at,
        })
        total += converted
        update_marks.append(updated_at)

    last_update = max(update_marks) if update_marks else None
    return {
        'wallets': items,
        'total': total,
        'base_currency': base_currency,
        'last_update': last_update,
    }


def _get_or_create_portfolio(portfolios, user_id):
    """Fetch portfolio entry or create a new one."""
    record = find_portfolio(portfolios, user_id)
    if record:
        return record
    record = {
        'user_id': user_id,
        'wallets': {},
    }
    portfolios.append(record)
    return record


def _get_wallet(record, currency_code):
    """Return wallet data for the currency, creating it if needed."""
    wallets = record.setdefault('wallets', {})
    wallet_data = wallets.get(currency_code)
    if not wallet_data:
        wallet_data = {'currency_code': currency_code, 'balance': 0.0}
        wallets[currency_code] = wallet_data
    return wallet_data


def buy_currency(user_id, currency_code, amount):
    """Buy currency using USD funds."""
    currency_code = currency_code.upper()
    if not is_currency_code(currency_code):
        raise ValueError('Некорректный код валюты')
    if not is_amount_valid(amount):
        raise ValueError("'amount' должен быть положительным числом")
    amount = float(amount)

    portfolios = load_portfolios()
    record = _get_or_create_portfolio(portfolios, user_id)

    target_wallet_data = _get_wallet(record, currency_code)
    usd_wallet_data = _get_wallet(record, 'USD')

    target_wallet = Wallet(currency_code, target_wallet_data.get('balance', 0.0))
    usd_wallet = Wallet('USD', usd_wallet_data.get('balance', 0.0))

    rate, updated_at = get_exchange_rate(currency_code, 'USD')
    cost = amount * rate

    #if cost > usd_wallet.balance:
    #    raise ValueError('Недостаточно средств в USD')

    before_target = target_wallet.balance
    before_usd = usd_wallet.balance

    target_wallet.deposit(amount)
    #usd_wallet.withdraw(cost)

    target_wallet_data['balance'] = target_wallet.balance
    usd_wallet_data['balance'] = usd_wallet.balance
    save_portfolios(portfolios)

    return {
        'currency_code': currency_code,
        'amount': amount,
        'rate': rate,
        'cost': cost,
        'wallet_before': before_target,
        'wallet_after': target_wallet.balance,
        'usd_before': before_usd,
        'usd_after': usd_wallet.balance,
        'updated_at': updated_at,
    }


def sell_currency(user_id, currency_code, amount):
    """Sell currency and credit USD funds."""
    currency_code = currency_code.upper()
    if not is_currency_code(currency_code):
        raise ValueError('Некорректный код валюты')
    if not is_amount_valid(amount):
        raise ValueError("'amount' должен быть положительным числом")
    amount = float(amount)

    portfolios = load_portfolios()
    record = _get_or_create_portfolio(portfolios, user_id)
    wallets = record.setdefault('wallets', {})
    if currency_code not in wallets:
        raise ValueError(f"У вас нет кошелька '{currency_code}'")

    target_wallet_data = wallets[currency_code]
    usd_wallet_data = _get_wallet(record, 'USD')

    target_wallet = Wallet(currency_code, target_wallet_data.get('balance', 0.0))
    usd_wallet = Wallet('USD', usd_wallet_data.get('balance', 0.0))

    if amount > target_wallet.balance:
        raise ValueError(f"Недостаточно средств: доступно {target_wallet.balance:.4f} {currency_code}, требуется {amount:.4f} {currency_code}")

    rate, updated_at = get_exchange_rate(currency_code, 'USD')
    revenue = amount * rate

    before_target = target_wallet.balance
    before_usd = usd_wallet.balance

    target_wallet.withdraw(amount)
    usd_wallet.deposit(revenue)

    target_wallet_data['balance'] = target_wallet.balance
    usd_wallet_data['balance'] = usd_wallet.balance
    save_portfolios(portfolios)

    return {
        'currency_code': currency_code,
        'amount': amount,
        'rate': rate,
        'revenue': revenue,
        'wallet_before': before_target,
        'wallet_after': target_wallet.balance,
        'usd_before': before_usd,
        'usd_after': usd_wallet.balance,
        'updated_at': updated_at,
    }


def fetch_rate(from_currency, to_currency):
    """Fetch current exchange rate for the currency pair."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    if not is_currency_code(from_currency) or not is_currency_code(to_currency):
        raise ValueError('Некорректные коды валют')

    rate, updated_at = get_exchange_rate(from_currency, to_currency)
    inverse = None
    if from_currency != to_currency:
        if rate == 0:
            raise ValueError('Курс недоступен')
        inverse = 1 / rate
    return {
        'from': from_currency,
        'to': to_currency,
        'rate': rate,
        'inverse': inverse,
        'updated_at': updated_at,
    }

