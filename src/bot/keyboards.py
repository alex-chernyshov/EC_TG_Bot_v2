from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.lang_pack.base import BaseLangPack


def get_main_keyboard(langpack: BaseLangPack) -> ReplyKeyboardMarkup:
    """Get the main persistent keyboard for registered users."""
    keyboard = [
        [KeyboardButton(langpack.BTN_POWER_STATUS, api_kwargs={"style": "primary"})],
        [KeyboardButton(langpack.BTN_GEN_STATUS, api_kwargs={"style": "primary"})],
        [KeyboardButton(langpack.BTN_SCHEDULE, api_kwargs={"style": "primary"})],
        [
            KeyboardButton(langpack.BTN_SETTINGS),
            KeyboardButton(langpack.BTN_REPORT_ERROR, api_kwargs={"style": "danger"}),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_night_sound_choice_keyboard(langpack: BaseLangPack) -> InlineKeyboardMarkup:
    """Get inline keyboard for night sound preference choice.

    Buttons are numbered; the matching options are listed in the message text (see get_night_sound_options_text).
    """
    keyboard = [
        [
            InlineKeyboardButton("1️⃣", callback_data="night_sound_yes"),
            InlineKeyboardButton("2️⃣", callback_data="night_sound_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_night_sound_options_text(langpack: BaseLangPack) -> str:
    """Numbered explanation of the night sound keyboard buttons."""
    return f"1️⃣ {langpack.OPT_NIGHT_SOUND_ON}\n2️⃣ {langpack.OPT_NIGHT_SOUND_OFF}"


def get_notification_choice_keyboard(langpack: BaseLangPack) -> InlineKeyboardMarkup:
    """Get inline keyboard for notification preference choice."""
    keyboard = [
        [
            InlineKeyboardButton(langpack.INLINE_BTN_YES, callback_data="notif_yes"),
            InlineKeyboardButton(langpack.INLINE_BTN_NO, callback_data="notif_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
