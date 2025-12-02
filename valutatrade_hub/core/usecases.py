from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    current_time_iso,
    find_portfolio,
    find_user,
    generate_salt,
    get_exchange_rate,
    hash_password,
    is_amount_valid,
    load_portfolios,
    load_users,
    next_user_id,
    save_portfolios,
    save_users,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader

_settings = SettingsLoader()
BASE_CURRENCY_CODE = (_settings.get('default_base_currency') or 'USD').strip().upper()


def _initial_base_balance():
    raw_value = _settings.get('initial_base_balance', 1000.0)
    try:
        amount = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    return max(amount, 0.0)


INITIAL_BASE_BALANCE = _initial_base_balance()


@log_action('REGISTER')
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
    base_wallets = {}
    if INITIAL_BASE_BALANCE > 0:
        base_wallets[BASE_CURRENCY_CODE] = {
            'currency_code': BASE_CURRENCY_CODE,
            'balance': INITIAL_BASE_BALANCE,
        }
    portfolios.append({
        'user_id': user_id,
        'wallets': base_wallets,
    })
    save_portfolios(portfolios)

    return {
        'user_id': user_id,
        'username': username,
    }


@log_action('LOGIN')
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


def get_portfolio_overview(user_id, base_currency=BASE_CURRENCY_CODE):
    """Return converted balances for all user wallets."""
    base_currency = (base_currency or BASE_CURRENCY_CODE).strip().upper()
    get_currency(base_currency)

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


@log_action('BUY', verbose=True)
def buy_currency(user_id, currency_code, amount):
    """Buy currency using base funds."""
    currency_code = currency_code.strip().upper()
    get_currency(currency_code)
    if not is_amount_valid(amount):
        raise ValueError("'amount' должен быть положительным числом")
    amount = float(amount)

    portfolios = load_portfolios()
    record = _get_or_create_portfolio(portfolios, user_id)

    target_wallet_data = _get_wallet(record, currency_code)
    base_wallet_data = _get_wallet(record, BASE_CURRENCY_CODE)

    same_currency_as_base = currency_code == BASE_CURRENCY_CODE
    target_wallet = Wallet(currency_code, target_wallet_data.get('balance', 0.0))
    base_wallet = (
        target_wallet
        if same_currency_as_base
        else Wallet(BASE_CURRENCY_CODE, base_wallet_data.get('balance', 0.0))
    )
    rate, updated_at = get_exchange_rate(currency_code, BASE_CURRENCY_CODE)
    cost = amount * rate

    before_target = target_wallet.balance
    before_base = base_wallet.balance

    base_wallet.withdraw(cost)
    target_wallet.deposit(amount)

    target_wallet_data['balance'] = target_wallet.balance
    if same_currency_as_base:
        base_wallet_data['balance'] = target_wallet.balance
        base_after = target_wallet.balance
    else:
        base_wallet_data['balance'] = base_wallet.balance
        base_after = base_wallet.balance
    save_portfolios(portfolios)

    return {
        'user_id': user_id,
        'currency_code': currency_code,
        'amount': amount,
        'rate': rate,
        'cost': cost,
        'wallet_before': before_target,
        'wallet_after': target_wallet.balance,
        'usd_before': before_base,
        'usd_after': base_after,
        'base_before': before_base,
        'base_after': base_after,
        'base_currency': BASE_CURRENCY_CODE,
        'updated_at': updated_at,
    }


@log_action('SELL', verbose=True)
def sell_currency(user_id, currency_code, amount):
    """Sell currency and credit base funds (base sales only withdraw)."""
    currency_code = currency_code.strip().upper()
    get_currency(currency_code)
    if not is_amount_valid(amount):
        raise ValueError("'amount' должен быть положительным числом")
    amount = float(amount)

    portfolios = load_portfolios()
    record = _get_or_create_portfolio(portfolios, user_id)
    wallets = record.setdefault('wallets', {})
    if currency_code not in wallets:
        raise InsufficientFundsError(0.0, amount, currency_code)

    target_wallet_data = wallets[currency_code]
    base_wallet_data = _get_wallet(record, BASE_CURRENCY_CODE)

    target_wallet = Wallet(currency_code, target_wallet_data.get('balance', 0.0))
    base_wallet = Wallet(BASE_CURRENCY_CODE, base_wallet_data.get('balance', 0.0))

    same_currency_as_base = currency_code == BASE_CURRENCY_CODE
    rate, updated_at = get_exchange_rate(currency_code, BASE_CURRENCY_CODE)
    revenue = amount * rate

    before_target = target_wallet.balance
    before_base = base_wallet.balance

    target_wallet.withdraw(amount)
    # Selling the base currency keeps funds in the same wallet, so we do not re-credit them.
    if not same_currency_as_base:
        base_wallet.deposit(revenue)

    target_wallet_data['balance'] = target_wallet.balance
    if same_currency_as_base:
        base_wallet_data['balance'] = target_wallet.balance
        base_after = target_wallet.balance
    else:
        base_wallet_data['balance'] = base_wallet.balance
        base_after = base_wallet.balance
    save_portfolios(portfolios)

    return {
        'user_id': user_id,
        'currency_code': currency_code,
        'amount': amount,
        'rate': rate,
        'revenue': revenue,
        'wallet_before': before_target,
        'wallet_after': target_wallet.balance,
        'usd_before': before_base,
        'usd_after': base_after,
        'base_before': before_base,
        'base_after': base_after,
        'base_currency': BASE_CURRENCY_CODE,
        'updated_at': updated_at,
    }


def fetch_rate(from_currency, to_currency):
    """Fetch current exchange rate for the currency pair."""
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    get_currency(from_currency)
    get_currency(to_currency)

    try:
        rate, updated_at = get_exchange_rate(from_currency, to_currency)
    except ValueError as error:
        raise ApiRequestError(str(error))
    inverse = None
    if from_currency != to_currency:
        if rate == 0:
            raise ApiRequestError('Курс недоступен')
        inverse = 1 / rate
    return {
        'from': from_currency,
        'to': to_currency,
        'rate': rate,
        'inverse': inverse,
        'updated_at': updated_at,
    }

