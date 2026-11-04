import os

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_update, button_rate_limited, registered_only
from src.dtek import fetch_today_schedule, today_label
from src.logger.main import logger


@button_rate_limited
@registered_only
async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u_identity = get_user_identity_from_update(update)
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(
        update.effective_user.language_code
    )
    keyboard = get_main_keyboard(langpack)

    group = os.getenv("DTEK_GROUP")
    if not group:
        logger.bind(username=u_identity).error("DTEK_GROUP is not set")
        await update.message.reply_text(langpack.MSG_SCHEDULE_UNAVAILABLE, reply_markup=keyboard)
        return

    logger.bind(username=u_identity).info("📅 User requested schedule")

    try:
        updated, intervals = await fetch_today_schedule(group)
    except Exception:
        logger.bind(username=u_identity).exception("Failed to fetch DTEK schedule")
        await update.message.reply_text(langpack.MSG_SCHEDULE_UNAVAILABLE, reply_markup=keyboard)
        return

    lines = [f"{langpack.MSG_SCHEDULE_TITLE} {today_label()} ({langpack.WORD_GROUP} {group})", ""]
    if intervals:
        lines += [f"🪫 {start} – {end}" for start, end in intervals]
    else:
        lines.append(langpack.MSG_SCHEDULE_NO_OUTAGES)
    lines += ["", f"{langpack.MSG_SCHEDULE_UPDATED} {updated}"]

    await update.message.reply_text("\n".join(lines), reply_markup=keyboard)
