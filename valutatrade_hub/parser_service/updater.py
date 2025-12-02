"""Orchestrate fetching rates from external providers."""

import logging
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service import storage


def _now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_timestamp(value):
    """Parse ISO-8601 timestamps with a trailing Z (UTC)."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class RatesUpdater:
    """Fetch rates from API clients and persist them."""

    def __init__(self, clients, logger=None):
        if not clients:
            raise ValueError("Не переданы клиенты для обновления курсов")
        self.clients = list(clients)
        base_logger = logger or setup_logging()
        if hasattr(base_logger, "getChild"):
            self.logger = base_logger.getChild("parser")
        else:
            self.logger = logging.getLogger("valutatrade.parser")
        storage.ensure_history_store()
        storage.ensure_rates_snapshot()

    def run_update(self, selected=None):
        selected_set = None
        if selected:
            if isinstance(selected, str):
                selected_set = {selected.lower()}
            else:
                selected_set = {name.lower() for name in selected}
        self.logger.info("Начато обновление курсов")

        collected = {}
        errors = []
        details = []
        attempted = False
        for client in self.clients:
            if selected_set and client.name.lower() not in selected_set:
                continue
            attempted = True
            self.logger.info("Запрос к %s", client.source_name)
            try:
                payload = client.fetch_rates()
            except ApiRequestError as error:
                message = str(error)
                self.logger.error("Ошибка при обращении к %s: %s", client.source_name, message)
                errors.append({"source": client.source_name, "message": message})
                details.append(
                    {
                        "source": client.source_name,
                        "slug": client.name,
                        "status": "error",
                        "message": message,
                    }
                )
                continue

            rates = payload.get("rates") or {}
            meta = payload.get("meta") or {}
            timestamp = payload.get("timestamp") or _now_iso()
            self.logger.info("Получено %s курсов от %s", len(rates), client.source_name)
            details.append(
                {
                    "source": client.source_name,
                    "slug": client.name,
                    "status": "ok",
                    "count": len(rates),
                }
            )
            for pair, value in rates.items():
                collected[pair] = {
                    "rate": float(value),
                    "source": payload.get("source") or client.source_name,
                    "timestamp": timestamp,
                    "meta": meta.get(pair, {}),
                }

        if not attempted:
            raise ValueError("Не найдено ни одного клиента для выбранного источника")
        if not collected and not errors:
            raise ApiRequestError("Не удалось получить данные ни от одного сервиса")

        snapshot = storage.load_rates_snapshot()
        pairs = snapshot.get("pairs") or {}
        updated = 0
        for pair, info in collected.items():
            existing = pairs.get(pair)
            existing_ts = _parse_timestamp(existing.get("updated_at")) if existing else None
            new_ts = _parse_timestamp(info["timestamp"])
            if existing_ts and new_ts and existing_ts >= new_ts:
                continue
            pairs[pair] = {
                "rate": info["rate"],
                "updated_at": info["timestamp"],
                "source": info["source"],
            }
            history_entry = {
                "id": f"{pair}_{info['timestamp']}",
                "from_currency": pair.split("_")[0],
                "to_currency": pair.split("_")[1],
                "rate": info["rate"],
                "timestamp": info["timestamp"],
                "source": info["source"],
                "meta": info.get("meta") or {},
            }
            storage.append_history_entry(history_entry)
            updated += 1

        if collected:
            parsed_pairs = []
            for info in collected.values():
                parsed_value = _parse_timestamp(info["timestamp"])
                if parsed_value:
                    parsed_pairs.append((parsed_value, info["timestamp"]))
            if parsed_pairs:
                last_refresh = max(parsed_pairs)[1]
            else:
                last_refresh = _now_iso()
        else:
            last_refresh = snapshot.get("last_refresh") or _now_iso()
        snapshot["pairs"] = pairs
        snapshot["last_refresh"] = last_refresh
        snapshot["source"] = "ParserService"
        storage.save_rates_snapshot(snapshot)

        self.logger.info("Обновление завершено. Успешно обновлено %s пар.", updated)
        if errors:
            for error in errors:
                self.logger.warning("Источник %s завершился с ошибкой: %s", error["source"], error["message"])

        return {
            "updated_count": updated,
            "errors": errors,
            "last_refresh": last_refresh,
            "details": details,
            "pairs": pairs,
        }


__all__ = ["RatesUpdater"]
