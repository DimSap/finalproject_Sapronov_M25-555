import hashlib
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError


class User:
    """User entity."""

    def __init__(self, user_id, username, password, salt, registration_date):
        self._user_id = user_id
        self._username = None
        self.username = username
        self._salt = salt
        self._hashed_password = None
        self.change_password(password)
        self._registration_date = registration_date

    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        if not value:
            raise ValueError('Username cannot be empty')
        self._username = value

    @property
    def hashed_password(self):
        return self._hashed_password

    @property
    def salt(self):
        return self._salt

    @property
    def registration_date(self):
        return self._registration_date

    def get_user_info(self):
        """Return public user info."""
        info = {
            'user_id': self._user_id,
            'username': self._username,
        }
        if isinstance(self._registration_date, datetime):
            info['registration_date'] = self._registration_date.isoformat()
        else:
            info['registration_date'] = self._registration_date
        return info

    def change_password(self, new_password):
        """Hash and save a new password."""
        if len(new_password) < 4:
            raise ValueError('Password must be at least 4 characters long')
        combined = (new_password + self._salt).encode('utf-8')
        self._hashed_password = hashlib.sha256(combined).hexdigest()

    def verify_password(self, password):
        """Check password against the stored hash."""
        combined = (password + self._salt).encode('utf-8')
        hashed = hashlib.sha256(combined).hexdigest()
        return hashed == self._hashed_password


class Wallet:
    """Wallet for a single currency."""

    def __init__(self, currency_code, balance=0.0):
        self.currency_code = currency_code
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError('Balance must be numeric')
        if value < 0:
            raise ValueError('Balance cannot be negative')
        self._balance = float(value)

    def deposit(self, amount):
        """Add funds to the wallet."""
        if amount <= 0:
            raise ValueError('Amount must be positive')
        self._balance += amount

    def withdraw(self, amount):
        """Remove funds if balance permits."""
        if amount <= 0:
            raise ValueError('Amount must be positive')
        if amount > self._balance:
            raise InsufficientFundsError(self._balance, amount, self.currency_code)
        self._balance -= amount

    def get_balance_info(self):
        """Return wallet balance details."""
        return {
            'currency_code': self.currency_code,
            'balance': self._balance,
        }


class Portfolio:
    """Collection of user wallets."""

    def __init__(self, user, wallets=None):
        self._user = user
        self._user_id = user.user_id if hasattr(user, 'user_id') else user
        self._wallets = {}
        if wallets:
            for code, wallet in wallets.items():
                self._wallets[code] = wallet

    @property
    def user(self):
        return self._user

    @property
    def wallets(self):
        return dict(self._wallets)

    def add_currency(self, currency_code):
        """Create a wallet for a new currency."""
        if currency_code in self._wallets:
            raise ValueError('Currency already exists in portfolio')
        self._wallets[currency_code] = Wallet(currency_code)

    def get_total_value(self, base_currency='USD'):
        """Calculate total portfolio value in base currency."""
        exchange_rates = {
            'USD': 1.0,
            'EUR': 1.1,
            'BTC': 60000.0,
            'ETH': 3000.0,
        }
        if base_currency not in exchange_rates:
            raise ValueError('Unknown base currency')
        total_in_usd = 0.0
        for wallet in self._wallets.values():
            if wallet.currency_code not in exchange_rates:
                raise ValueError('Missing exchange rate for currency')
            total_in_usd += wallet.balance * exchange_rates[wallet.currency_code]
        if base_currency == 'USD':
            return total_in_usd
        return total_in_usd / exchange_rates[base_currency]

    def get_wallet(self, currency_code):
        """Return wallet by currency."""
        return self._wallets.get(currency_code)

