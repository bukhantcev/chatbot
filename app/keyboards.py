from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.prompts import LEVEL_NAMES


LEVEL_BUTTON_TEXT = "Уровень"
RESET_BUTTON_TEXT = "Сбросить контекст"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=LEVEL_BUTTON_TEXT),
                KeyboardButton(text=RESET_BUTTON_TEXT),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши Саше",
    )


def levels_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{level}. {name}", callback_data=f"level:{level}")]
        for level, name in LEVEL_NAMES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reset_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, сбросить", callback_data="reset:confirm"),
                InlineKeyboardButton(text="Отмена", callback_data="reset:cancel"),
            ]
        ]
    )
