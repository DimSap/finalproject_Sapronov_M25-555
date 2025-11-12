import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from valutatrade_hub.constants import DEFAULT_RATES, RATE_FRESH_MINUTES, RATE_SOURCE

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
USERS_FILE = DATA_DIR / 'users.json'
PORTFOLIOS_FILE = DATA_DIR / 'portfolios.json'
RATES_FILE = DATA_DIR / 'rates.json'

FRESH_LIMIT = timedelta(minutes=RATE_FRESH_MINUTES)


def ensure_file(path, default):
    """Create a file with default content if it does not exist."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as fh:
            json.dump(default, fh, ensure_ascii=True, indent=2)


def load_json(path, default):
    """Load JSON data, creating the file with default content when missing."""
    ensure_file(path, default)
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def save_json(path, data):
    """Persist JSON data to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2)


def load_users():
    """Return the list of users from storage."""
    return load_json(USERS_FILE, [])


def save_users(users):
    """Save the list of users to storage."""
    save_json(USERS_FILE, users)


def load_portfolios():
    """Return all stored portfolios."""
    return load_json(PORTFOLIOS_FILE, [])


def save_portfolios(portfolios):
    """Persist the provided portfolios list."""
    save_json(PORTFOLIOS_FILE, portfolios)


def load_rates():
    """Return cached currency rates."""
    return load_json(RATES_FILE, {})


def save_rates(rates):
    """Save currency rates to storage."""
    save_json(RATES_FILE, rates)


def generate_salt():
    """Create a random salt for password hashing."""
    return secrets.token_hex(8)


def hash_password(password, salt):
    """Return a SHA-256 hash for the given password and salt."""
    combined = (password + salt).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()


def next_user_id(users):
    """Generate the next user identifier."""
    if not users:
        return 1
    return max(user['user_id'] for user in users) + 1


def find_user(users, username):
    """Find a user record by username."""
    for user in users:
        if user['username'] == username:
            return user
    return None


def find_portfolio(portfolios, user_id):
    """Locate portfolio data by user id."""
    for portfolio in portfolios:
        if portfolio['user_id'] == user_id:
            return portfolio
    return None


def current_time_iso():
    """Return current UTC time formatted as ISO string."""
    return datetime.utcnow().replace(microsecond=0).isoformat()


def is_currency_code(value):
    """Validate that value looks like an upper-case currency code."""
    return isinstance(value, str) and value.strip() and value.upper() == value


def is_amount_valid(value):
    """Check that provided amount is a positive number."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def get_rate_key(base, quote):
    """Compose a storage key for the currency pair."""
    return f'{base}_{quote}'


def read_rate_entry(rates, key):
    """Retrieve a stored rate entry by key."""
    entry = rates.get(key)
    if isinstance(entry, dict) and 'rate' in entry:
        return entry
    return None


def default_rate(base, quote):
    """Return a fallback exchange rate for the currency pair."""
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
    """Return exchange rate and timestamp for the requested pair."""
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
    rates['source'] = RATE_SOURCE
    rates['last_refresh'] = timestamp
    save_rates(rates)
    return rate, timestamp

