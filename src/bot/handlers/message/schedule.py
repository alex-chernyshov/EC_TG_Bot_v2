import os
from datetime import datetime

from sqlalchemy import desc, select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.constants import KYIV_TZ
from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_update, button_rate_limited, registered_only
from src.db.models import DtekSchedule
from src.dtek import outage_intervals
from src.logger.main import logger


@button_rate_limited
@registered_only
async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u_identity = get_user_identity_from_update(update)
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(
        update.effective_user.language_code
    )
    keyboard = get_main_keyboard(langpack)
    log = logger.bind(username=u_identity)

    group = os.getenv("DTEK_GROUP")
    if not group:
        log.error("DTEK_GROUP is not set")
        await update.message.reply_text(langpack.MSG_SCHEDULE_UNAVAILABLE, reply_markup=keyboard)
        return

    log.info("📅 User requested schedule")

    # Latest day up to today: if the scheduler couldn't fetch today's data yet, the last known day is shown
    # (the title carries its date).
    today = datetime.now(KYIV_TZ).date()
    session_factory = context.application.bot_data["session_factory"]
    async with session_factory() as session:
        result = await session.execute(
            select(DtekSchedule)
            .where(DtekSchedule.group_code == group, DtekSchedule.day <= today)
            .order_by(desc(DtekSchedule.day))
            .limit(1)
        )
        schedule = result.scalar_one_or_none()

    if schedule is None:
        log.warning(f"No DTEK schedule in DB for group={group}")
        await update.message.reply_text(langpack.MSG_SCHEDULE_UNAVAILABLE, reply_markup=keyboard)
        return

    log.info(
        f"Retrieved latest [DTEK {group}] schedule day={schedule.day.isoformat()}, "
        f"site_updated={schedule.site_updated}, date_fetched={schedule.date_fetched.isoformat()}"
    )

    intervals = outage_intervals(schedule.hours)
    lines = [f"{langpack.MSG_SCHEDULE_TITLE} {schedule.day:%d.%m.%Y} ({langpack.WORD_GROUP} {group})", ""]
    if intervals:
        lines += [f"🪫 {start} – {end}" for start, end in intervals]
    else:
        lines.append(langpack.MSG_SCHEDULE_NO_OUTAGES)
    lines += ["", f"{langpack.MSG_SCHEDULE_UPDATED} {schedule.site_updated}"]

    await update.message.reply_text("\n".join(lines), reply_markup=keyboard)
