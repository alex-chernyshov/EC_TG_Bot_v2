from src.bot.lang_pack.base import BaseLangPack


class RULangPack(BaseLangPack):
    BTN_POWER_STATUS = "💡 Свет 💡"
    BTN_GEN_STATUS = "🔋 Генератор 🔋"
    BTN_SCHEDULE = "📅 График 📅"
    BTN_SETTINGS = "⚙️ Настройки ⚙️"
    BTN_REPORT_ERROR = "🆘 Сообщить об ошибке 🆘"

    OPT_NIGHT_SOUND_ON = "🔊 Со звуком ночью"
    OPT_NIGHT_SOUND_OFF = "🔇 Беззвучно ночью (без звука)"
    INLINE_BTN_YES = "Да"
    INLINE_BTN_NO = "Нет"

    MSG_USE_KEYBOARD = "Используйте клавиатуру ниже для взаимодействия с ботом 👇"
    MSG_NOTIFICATIONS_ON = "Отлично! Уведомления включены. 🔔\n\nВыберите, как будут приходить ночные уведомления (с 22:00 до 08:00).\nВ беззвучном режиме они всё равно придут, просто без звука:"
    MSG_PRESS_OPTION = "Нажмите 1 или 2 👇"
    MSG_WELCOME_USER = "Добро пожаловать, {username}!"
    MSG_Q_ENABLE_NOTIFS = "Хотите включить уведомления (бот самостоятельно будет отправлять сообщение в чат, в моменты когда свет включают/выключают)?"
    MSG_GEN_NOT_REQUIRED = "⚡️ В доме есть свет ⚡️\n\nГенератор не требуется"
    MSG_GEN_ON = "🔋 *Генератор РАБОТАЕТ* 🔋"
    MSG_GEN_OFF = "🪫 *Генератор НЕ РАБОТАЕТ* 🪫"
    MSG_GEN_SHOULD_BE_OFF = "⚠️ _Генератор работает, но, согласно расписанию, его должны *ВЫКЛЮЧИТЬ*\\!_"
    MSG_GEN_SHOULD_BE_ON = "⚠️ _Генератор выключен, но, согласно расписанию, его должны *ВКЛЮЧИТЬ*\\!_"
    MSG_GEN_TIME_TILL_OFF = "⏳ Согласно расписанию, до отключения:"
    MSG_GEN_TIME_TILL_ON = "⏳ Согласно расписанию, до включения:"
    MSG_POWER_STATUS_NOT_AVAILABLE = "⚠️ Информация пока недоступна. Пожалуйста, попробуйте позже."
    MSG_SCHEDULE_TITLE = "📅 Отключения на"
    MSG_SCHEDULE_NO_OUTAGES = "Отключений не запланировано ✅"
    MSG_SCHEDULE_UPDATED = "Обновлено:"
    MSG_SCHEDULE_UNAVAILABLE = "⚠️ График пока недоступен. Пожалуйста, попробуйте позже."
    MSG_SCHEDULE_SOURCE = "Данные получены с официального сайта ДТЭК"
    MSG_POWER_IS_ON = "🟢 *Электричество ЕСТЬ\\!* 🟢"
    MSG_POWER_IS_OFF = "🔴 *Электричества НЕТ* 🔴"
    MSG_POWER_TURN_ON_TIME = "📅 Время включения"
    MSG_POWER_TURN_OFF_TIME = "📅 Время отключения"
    MSG_REPORT_ERROR = (
        "Если у Вас что\\-то не работает, то напишите мне в личку, все починим и настроим 🤝\n\n@AlexFoxalt"
    )
    MSG_USER_NOT_FOUND = "Пользователь не найден. Пожалуйста, используйте команду /start для регистрации."
    MSG_NOTIFS_DISABLED = "Уведомления отключены. Вы можете изменить это позже."
    MSG_REGISTRATION_COMPLETED = "Регистрация завершена! Теперь Вы можете использовать бота 🎉"
    MSG_NOTIF_NIGHT_SOUND = "Звуковое оповещение в ночное время"
    MSG_SETTINGS_UPDATED = "Настройки обновлены ✅"
    MSG_TIME_SINCE_SHUTDOWN = "⏳ С момента отключения прошло"
    MSG_TIME_SINCE_POWER_ON = "⏳ С момента включения прошло"

    NOTIF_ATTENTION = "📢️  *ВНИМАНИЕ*  📢"
    NOTIF_POWER_TURN_ON_TIME = "⏳Свет был"
    NOTIF_POWER_TURN_OFF_TIME = "⏳Света не было"
    NOTIF_POWER_SURGE_WARN = "⚠️ Возможно, причиной стал скачок напряжения в электросети\\."
    NOTIF_FOOTER = "_Вы получили это сообщение, потому что включили уведомления в настройках бота\\. Их можно в любой момент отключить\\._"

    WORD_MINUTES = "мин"
    WORD_HOURS = "ч"
    WORD_GROUP = "группа"
    WORD_AND = "и"
    WORD_USER = "Пользователь"
    WORD_POWER = "Электричество"
    WORD_ENABLED_LOWER = "включено"
    WORD_DISABLED_LOWER = "выключено"

    ERR_BOT_NOT_INITIALIZED = "Бот некорректно инициализирован. Пожалуйста, свяжитесь с администратором."
    ERR_USER_NOT_FOUND = "Пользователь не найден. Пожалуйста, используйте команду /start еще раз."
    ERR_SESSION_EXPIRED = "Срок жизни сессии истек. Пожалуйста, воспользуйтесь командой /start заново."

    def __repr__(self) -> str:
        return "RU"
