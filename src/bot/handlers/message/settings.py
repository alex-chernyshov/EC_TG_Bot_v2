from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_settings_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import (
    get_user_identity_from_update,
    get_user_from_db,
    get_settings_summary,
    button_rate_limited,
    registered_only,
)
from src.logger.main import logger


@button_rate_limited
@registered_only
async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Settings' button - show current settings with a button to reconfigure them."""
    user = update.effective_user
    if user is None:
        logger.warning("Received settings request but effective_user is None")
        return

    u_identity = get_user_identity_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.bind(username=u_identity).error("Session factory not initialized in handle_settings")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    db_user = await get_user_from_db(session_factory, user.id)
    if db_user is None:
        logger.bind(username=u_identity).error("User not found in db during settings request")
        await update.message.reply_text(langpack.ERR_USER_NOT_FOUND)
        return

    logger.bind(username=u_identity).info("⚙️  User requested current settings")

    summary = get_settings_summary(langpack, db_user.notifs_enabled, db_user.night_notif_sound_enabled)
    await update.message.reply_text(
        f"{langpack.MSG_CURRENT_SETTINGS}\n\n{summary}\n\n{langpack.MSG_RECONFIGURE_HINT}",
        reply_markup=get_settings_keyboard(langpack),
    )
