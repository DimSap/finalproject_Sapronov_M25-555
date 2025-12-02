"""File storage helpers for parser service artifacts."""

import json
from datetime import datetime

from valutatrade_hub.parser_service.config import get_parser_config

HISTORY_DEFAULT = []
RATES_DEFAULT = {"pairs": {}, "last_refresh": None}


def ensure_history_store():
    cfg = get_parser_config()
    _ensure_file(cfg.history_file_path, HISTORY_DEFAULT)


def ensure_rates_snapshot():
    cfg = get_parser_config()
    _ensure_file(cfg.rates_file_path, RATES_DEFAULT)


def load_history():
    cfg = get_parser_config()
    ensure_history_store()
    with cfg.history_file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "history" in data and isinstance(data["history"], list):
        return data["history"]
    raise ValueError("Некорректный формат файла exchange_rates.json")


def save_history(entries):
    cfg = get_parser_config()
    payload = list(entries)
    _atomic_write(cfg.history_file_path, payload)


def append_history_entry(entry):
    entries = load_history()
    entry_id = entry.get("id")
    if not entry_id:
        raise ValueError("У записи истории отсутствует идентификатор")
    for existing in entries:
        if existing.get("id") == entry_id:
            return False
    entries.append(entry)
    save_history(entries)
    return True


def load_rates_snapshot():
    cfg = get_parser_config()
    ensure_rates_snapshot()
    with cfg.rates_file_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return _normalize_rates_payload(raw)


def save_rates_snapshot(data):
    cfg = get_parser_config()
    normalized = _normalize_rates_payload(data)
    _atomic_write(cfg.rates_file_path, normalized)


def upsert_rate_pair(pair, rate, updated_at, source):
    snapshot = load_rates_snapshot()
    pairs = snapshot.setdefault("pairs", {})
    current = pairs.get(pair)
    current_ts = _parse_timestamp(current["updated_at"]) if _has_timestamp(current) else None
    new_ts = _parse_timestamp(updated_at)
    if current_ts and current_ts >= new_ts:
        return False
    pairs[pair] = {
        "rate": float(rate),
        "updated_at": updated_at,
        "source": source,
    }
    last_refresh = snapshot.get("last_refresh")
    if not last_refresh or _parse_timestamp(last_refresh) < new_ts:
        snapshot["last_refresh"] = updated_at
    save_rates_snapshot(snapshot)
    return True


def _ensure_file(path, default):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(default, handle, ensure_ascii=True, indent=2)


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
    tmp_path.replace(path)


def _normalize_rates_payload(raw):
    if not isinstance(raw, dict):
        return {"pairs": {}, "last_refresh": None}
    pairs = raw.get("pairs")
    if not isinstance(pairs, dict):
        pairs = {}
        for key, value in raw.items():
            if isinstance(value, dict) and "rate" in value:
                pairs[key] = value
    cleaned = {
        "pairs": pairs or {},
        "last_refresh": raw.get("last_refresh"),
    }
    source = raw.get("source")
    if source:
        cleaned["source"] = source
    return cleaned


def _parse_timestamp(value):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _has_timestamp(entry):
    return bool(entry and isinstance(entry, dict) and entry.get("updated_at"))


__all__ = [
    "append_history_entry",
    "ensure_history_store",
    "ensure_rates_snapshot",
    "load_history",
    "load_rates_snapshot",
    "save_history",
    "save_rates_snapshot",
    "upsert_rate_pair",
]

