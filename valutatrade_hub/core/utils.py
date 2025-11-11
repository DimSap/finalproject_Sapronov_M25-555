import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
USERS_FILE = DATA_DIR / 'users.json'
PORTFOLIOS_FILE = DATA_DIR / 'portfolios.json'
RATES_FILE = DATA_DIR / 'rates.json'

DEFAULT_RATES = {
    'USD_USD': 1.0,
    'EUR_USD': 1.0786,
    'BTC_USD': 59337.21,
    'RUB_USD': 0.01016,
    'ETH_USD': 3720.0,
}

FRESH_LIMIT = timedelta(minutes=5)


def ensure_file(path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as fh:
            json.dump(default, fh, ensure_ascii=True, indent=2)


def load_json(path, default):
    ensure_file(path, default)
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2)


def load_users():
    return load_json(USERS_FILE, [])


def save_users(users):
    save_json(USERS_FILE, users)


def load_portfolios():
    return load_json(PORTFOLIOS_FILE, [])


def save_portfolios(portfolios):
    save_json(PORTFOLIOS_FILE, portfolios)


def load_rates():
    return load_json(RATES_FILE, {})


def save_rates(rates):
    save_json(RATES_FILE, rates)


def generate_salt():
    return secrets.token_hex(8)


def hash_password(password, salt):
    combined = (password + salt).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()


def next_user_id(users):
    if not users:
        return 1
    return max(user['user_id'] for user in users) + 1


def find_user(users, username):
    for user in users:
        if user['username'] == username:
            return user
    return None


def find_portfolio(portfolios, user_id):
    for portfolio in portfolios:
        if portfolio['user_id'] == user_id:
            return portfolio
    return None


def current_time_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def is_currency_code(value):
    return isinstance(value, str) and value.strip() and value.upper() == value


def is_amount_valid(value):
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def get_rate_key(base, quote):
    return f'{base}_{quote}'


def read_rate_entry(rates, key):
    entry = rates.get(key)
    if isinstance(entry, dict) and 'rate' in entry:
        return entry
    return None


def default_rate(base, quote):
    key = get_rate_key(base, quote)
    if key in DEFAULT_RATES:
        return DEFAULT_RATES[key]
    reverse_key = get_rate_key(quote, base)
    if reverse_key in DEFAULT_RATES:
        rate = DEFAULT_RATES[reverse_key]
        if rate == 0:
            raise ValueError('Курс недоступен')
        return 1 / rate
    if base == quote:
        return 1.0
    raise ValueError('Курс недоступен')


def get_exchange_rate(from_currency, to_currency):
    if from_currency == to_currency:
        return 1.0, current_time_iso()

    rates = load_rates()
    key = get_rate_key(from_currency, to_currency)
    entry = read_rate_entry(rates, key)
    if entry:
        updated_at = datetime.fromisoformat(entry['updated_at'])
        if datetime.utcnow() - updated_at <= FRESH_LIMIT:
            return entry['rate'], entry['updated_at']

    rate = default_rate(from_currency, to_currency)
    timestamp = current_time_iso()
    rates[key] = {
        'rate': rate,
        'updated_at': timestamp,
    }
    rates['source'] = 'StubService'
    rates['last_refresh'] = timestamp
    save_rates(rates)
    return rate, timestamp

