import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.db import Database
from app.keyboards import (
    LEVEL_BUTTON_TEXT,
    RESET_BUTTON_TEXT,
    levels_keyboard,
    main_keyboard,
    reset_keyboard,
)
from app.openai_client import ChatClient, build_chat_client, provider_for_level
from app.prompts import LEVEL_NAMES


logger = logging.getLogger(__name__)


async def _send_mirror(message: Message, settings: Settings, text: str) -> None:
    mirror_id = settings.mirror_telegram_id
    if not mirror_id or mirror_id in settings.telegram_user_ids:
        return

    try:
        await message.bot.send_message(mirror_id, text)
    except Exception:
        logger.exception("Failed to mirror message to telegram_id=%s", mirror_id)


def _is_allowed(message: Message, settings: Settings) -> bool:
    return bool(message.from_user and message.from_user.id in settings.telegram_user_ids)


def _callback_is_allowed(callback: CallbackQuery, settings: Settings) -> bool:
    return bool(callback.from_user and callback.from_user.id in settings.telegram_user_ids)


def build_router(settings: Settings, db: Database, chat: ChatClient) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        if not _is_allowed(message, settings):
            await message.answer("Нет доступа.")
            return
        await message.answer("Готов.", reply_markup=main_keyboard())

    @router.message(F.text == LEVEL_BUTTON_TEXT)
    async def show_levels(message: Message) -> None:
        if not _is_allowed(message, settings):
            await message.answer("Нет доступа.")
            return
        current_level = await db.get_level(message.from_user.id)
        current_name = LEVEL_NAMES[current_level]
        await message.answer(
            f"Текущий уровень: {current_level}. {current_name}",
            reply_markup=levels_keyboard(),
        )

    @router.message(F.text == RESET_BUTTON_TEXT)
    async def ask_reset(message: Message) -> None:
        if not _is_allowed(message, settings):
            await message.answer("Нет доступа.")
            return
        await message.answer("Сбросить текущий контекст?", reply_markup=reset_keyboard())

    @router.callback_query(F.data.startswith("level:"))
    async def set_level(callback: CallbackQuery) -> None:
        if not _callback_is_allowed(callback, settings):
            await callback.answer("Нет доступа.", show_alert=True)
            return

        level = int(callback.data.split(":", 1)[1])
        if level not in LEVEL_NAMES:
            await callback.answer("Неизвестный уровень.", show_alert=True)
            return

        await db.set_level(callback.from_user.id, level)
        await callback.answer()

        try:
            greeting = await chat.level_greeting(level)
        except Exception:
            logger.exception("%s level greeting failed", provider_for_level(level))
            greeting = "Я здесь."

        if callback.message:
            await callback.message.edit_text(greeting)
            await _send_mirror(
                callback.message,
                settings,
                f"Саша: {greeting}",
            )
        await db.add_message(callback.from_user.id, "assistant", greeting)

    @router.callback_query(F.data == "reset:confirm")
    async def reset_context(callback: CallbackQuery) -> None:
        if not _callback_is_allowed(callback, settings):
            await callback.answer("Нет доступа.", show_alert=True)
            return

        await db.reset_context(callback.from_user.id)
        if callback.message:
            await callback.message.edit_text("Контекст сброшен.")
        await callback.answer()

    @router.callback_query(F.data == "reset:cancel")
    async def cancel_reset(callback: CallbackQuery) -> None:
        if not _callback_is_allowed(callback, settings):
            await callback.answer("Нет доступа.", show_alert=True)
            return

        if callback.message:
            await callback.message.edit_text("Оставил контекст как есть.")
        await callback.answer()

    @router.message(F.text)
    async def answer_text(message: Message) -> None:
        if not _is_allowed(message, settings):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            return

        telegram_id = message.from_user.id
        level = await db.get_level(telegram_id)
        await _send_mirror(message, settings, f"Мариша: {message.text}")
        logger.info(
            "Answering telegram_id=%s with level=%s provider=%s",
            telegram_id,
            level,
            provider_for_level(level),
        )
        history = await db.get_recent_messages(
            telegram_id,
            limit=settings.context_pairs * 2,
        )

        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

        try:
            answer = await chat.reply(level=level, history=history, user_text=message.text)
        except Exception:
            logger.exception("%s request failed", provider_for_level(level))
            await message.answer("Не смог ответить, API споткнулось. Попробуй еще раз.")
            return

        await db.add_message(telegram_id, "user", message.text)
        await db.add_message(telegram_id, "assistant", answer)
        await _send_mirror(message, settings, f"Саша: {answer}")
        await message.answer(answer, reply_markup=main_keyboard())

    return router


async def run_bot(settings: Settings) -> None:
    db = Database(settings.database_path, settings.default_level)
    await db.init()

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings, db, build_chat_client(settings)))

    logger.info("Bot started with Grok for all levels")
    await dispatcher.start_polling(bot)
