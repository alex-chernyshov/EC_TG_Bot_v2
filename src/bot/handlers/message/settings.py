from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_notification_choice_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_update, button_rate_limited, registered_only
from src.logger.main import logger


@button_rate_limited
@registered_only
async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Notification settings' button - allow user to reconfigure notification preferences."""
    user = update.effective_user
    if user is None:
        logger.warning("Received reconfigure setting request but effective_user is None")
        return

    u_identity = get_user_identity_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.bind(username=u_identity).error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    logger.bind(username=u_identity).info("⚙️  User requested to reconfigure notification settings")

    # Start the notification preference flow (reuse registration flow)
    await update.message.reply_text(
        langpack.MSG_Q_ENABLE_NOTIFS,
        reply_markup=get_notification_choice_keyboard(langpack),
    )

    # Store user_id in context for callback handlers (same as registration flow)
    context.user_data["registering_user_id"] = user.id
    context.user_data["is_reconfiguration"] = True  # Mark as reconfiguration
    logger.bind(username=u_identity).info(
        "Started notification settings reconfiguration - waiting for notification preference..."
    )
