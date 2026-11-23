from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_notification_choice_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_query
from src.logger.main import logger


async def handle_settings_reconfigure(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Change settings' button - start the reconfiguration flow (reuses registration flow)."""
    query = update.callback_query
    if query is None:
        logger.warning("Received settings reconfigure callback but query is None")
        return

    u_identity = get_user_identity_from_query(query)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    await query.answer()

    # Store user_id in context for callback handlers (same as registration flow)
    context.user_data["registering_user_id"] = query.from_user.id
    context.user_data["is_reconfiguration"] = True

    await query.edit_message_text(
        langpack.MSG_Q_ENABLE_NOTIFS,
        reply_markup=get_notification_choice_keyboard(langpack),
    )
    logger.bind(username=u_identity).info(
        "Started notification settings reconfiguration - waiting for notification preference..."
    )
