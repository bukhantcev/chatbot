import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_user_ids: tuple[int, ...]
    mirror_telegram_id: int | None
    grok_api_key: str
    grok_model: str
    database_path: str
    context_pairs: int
    default_level: int


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _int_list_env(name: str) -> tuple[int, ...]:
    value = os.getenv(name)
    if not value:
        return ()

    result = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            parsed = int(item)
        except ValueError as exc:
            raise RuntimeError(f"{name} must be a comma-separated list of integers") from exc
        if parsed <= 0:
            raise RuntimeError(f"{name} values must be positive integers")
        result.append(parsed)

    return tuple(dict.fromkeys(result))


def load_settings() -> Settings:
    load_dotenv()

    context_pairs = _int_env("CONTEXT_PAIRS", 15)
    default_level = _int_env("DEFAULT_LEVEL", 1)
    telegram_user_ids = _int_list_env("TELEGRAM_USER_IDS")
    legacy_telegram_user_id = _int_env("TELEGRAM_USER_ID", 0)
    mirror_telegram_id = _int_env("MIRROR_TELEGRAM_ID", 0)

    if not telegram_user_ids and legacy_telegram_user_id > 0:
        telegram_user_ids = (legacy_telegram_user_id,)

    if not 1 <= context_pairs <= 30:
        raise RuntimeError("CONTEXT_PAIRS must be between 1 and 30")
    if not 1 <= default_level <= 5:
        raise RuntimeError("DEFAULT_LEVEL must be between 1 and 5")
    if not telegram_user_ids:
        raise RuntimeError("TELEGRAM_USER_IDS is required")

    grok_api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")

    if not grok_api_key:
        raise RuntimeError("GROK_API_KEY is required")

    return Settings(
        telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
        telegram_user_ids=telegram_user_ids,
        mirror_telegram_id=mirror_telegram_id if mirror_telegram_id > 0 else None,
        grok_api_key=grok_api_key,
        grok_model=os.getenv("GROK_MODEL", "grok-4.3"),
        database_path=os.getenv("DATABASE_PATH", "data/bot.sqlite3"),
        context_pairs=context_pairs,
        default_level=default_level,
    )
