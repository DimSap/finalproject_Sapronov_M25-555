## ValutaTrade Hub

CLI-платформа для учебного управления мультивалютным портфелем: регистрация пользователей, покупка/продажа валют, просмотр курсов и обновление локального кеша из внешних API.

### Возможности
- хранение пользователей и кошельков в `data/*.json`;
- операции `register`, `login`, `show-portfolio`, `buy`, `sell`, `get-rate`;
- обновление курсов из CoinGecko и ExchangeRate-API (через Parser Service);
- кеширование курсов с TTL и fallback на дефолтные значения;
- подробное логирование действий и ошибок в `logs/actions.log`.
- автоматический стартовый депозит 1000 USD (значение настраивается `initial_base_balance`).

---

## Структура проекта
```
valutatrade_hub/
├── core/            # модели, usecase'ы, утилиты и исключения
├── cli/             # только обработчики аргументов и вывод
├── infra/           # SettingsLoader (singleton) и config.json
├── parser_service/  # HTTP-клиенты, updater и storage
├── decorators.py    # log_action + handle_errors
├── logging_config.py
├── main.py          # точка входа (poetry run project)
data/
├── users.json
├── portfolios.json
├── rates.json
└── exchange_rates.json
Makefile
pyproject.toml
```

## Установка
make install     
```

При необходимости активируйте окружение: `poetry shell`.

---

## Запуск CLI
- Интерактивный режим: `make project`
- Одноразовая команда: `poetry run project <command> [args]`

Примеры:
```bash
poetry run project register --username alice --password secret
poetry run project login --username alice --password secret
poetry run project buy --currency BTC --amount 0.01
poetry run project show-portfolio --base USD
poetry run project get-rate --from BTC --to USD
poetry run project update-rates --source coingecko
poetry run project show-rates --currency BTC --top 5
```

---

## Команды CLI (кратко)
- `register --username --password` — создаёт пользователя и начисляет стартовый депозит (по умолчанию 1000 USD).
- `login --username --password` — активирует сессию (хранится в памяти CLI).
- `show-portfolio [--base USD]` — выводит баланс кошельков + пересчёт в базовую валюту.
- `buy --currency XXX --amount N` — списывает базовую валюту и пополняет нужный кошелёк.
- `sell --currency XXX --amount N` — продаёт валюту, зачисляя базовую.
- `get-rate --from XXX --to YYY` — показывает курс и обратное значение.
- `update-rates [--source coingecko|exchangerate]` — запускает Parser Service.
- `show-rates [--currency XXX] [--base USD] [--top N]` — читает локальный кеш.

Ошибки домена (недостаточно средств, неизвестная валюта, устаревшие курсы) перехватываются в CLI и выводятся человекочитаемыми сообщениями.

---

## Кеш курсов и TTL
- Кеш хранится в `data/rates.json` (актуальные пары) и `data/exchange_rates.json` (история).
- Период свежести задаётся ключом `rates_ttl_seconds` в `config.json` (по умолчанию 300 секунд).
- После истечения TTL ядро пытается взять курс из кеша; при отсутствии свежих данных записывает fallback-значение (источник `StubService`), поэтому рекомендуется сразу выполнить `update-rates`, чтобы вернуть живые данные.

---

## Parser Service
1. Установите переменную окружения `EXCHANGERATE_API_KEY` (ключ сервиса https://www.exchangerate-api.com/).
2. Запустите `poetry run project update-rates` либо `make project` → `update-rates`.
3. Результаты сохранятся в `data/rates.json`, история пополнится атомарно, логи появятся в `logs/actions.log`.

Клиенты:
- CoinGecko — криптовалюты (`BTC`, `ETH`, `SOL`).
- ExchangeRate-API — фиат (`EUR`, `GBP`, `RUB`).

URL'ы клиентов, базовая валюта, списки крипто/фиат валют, таймаут запросов и имена источников настраиваются через `config.json` (`parser_*` ключи) или переменные окружения (`PARSER_COINGECKO_URL`, `PARSER_FIAT_CODES`, `PARSER_CRYPTO_CODES`, `PARSER_REQUEST_TIMEOUT`, и т.д.).

---

## Конфигурация
Все основные пути и параметры лежат в `config.json`:
- каталоги данных/логов;
- базовая валюта (`default_base_currency`);
- стартовый баланс новых пользователей (`initial_base_balance`, по умолчанию 1000 USD);
- размер лог-файла и формат сообщений;
- TTL курсов.

Из CLI можно в любой момент вызвать `poetry run python - <<'PY' ...` чтобы распечатать текущие настройки, либо редактировать файл вручную (приложение перечитывает его при старте).

---

## Логирование
- Действия (`register`, `buy`, `sell`, ...) пишутся в `logs/actions.log` с ротацией.
- Ошибки парсера/CLI также попадают в этот файл через `@log_action`.
- Формат логов задаётся в `config.json` (`log_format`).

---

## Сценарий демо
1. `register --username demo --password secret`.
2. `login --username demo --password secret`.
3. При необходимости увеличьте баланс базовой валюты (стартовые 1000 USD уже начислены автоматически).
4. `buy --currency BTC --amount 0.01`.
5. `sell --currency BTC --amount 0.005`.
6. `show-portfolio`.
7. `get-rate --from EUR --to USD`.
8. `update-rates` и `show-rates --currency BTC`.

Сценарий покрывает все требования демонстрации: happy-path + обновление курсов и сообщение об ошибке при недостатке средств.

Демо использования 

[![asciicast](https://asciinema.org/a/6LxLvIdW9B4YKLIH6kMHAf4u8.svg)](https://asciinema.org/a/6LxLvIdW9B4YKLIH6kMHAf4u8)
