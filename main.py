import os
import logging
from datetime import datetime, timedelta
from typing import List, Tuple
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# Загрузка .env
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Расписание
WORK_SCHEDULE = {
    '2025-06-21': {'type': 'day_off', 'available': [('09:00', '11:00')]},
    '2025-06-22': {'type': 'day_shift', 'work': ('08:00', '20:00'), 'travel': 90},
    '2025-06-23': {'type': 'night_shift', 'work': ('20:00', '08:00'), 'travel': 90},
    '2025-06-24': {'type': 'day_off', 'available': [('09:00', '23:59')]},
    '2025-06-25': {'type': 'day_off', 'available': [('00:00', '23:59')]},
}

STUDY_TOPICS = [
    "Основы Linux: файловая система, основные команды",
    "Работа с терминалом: pipes, перенаправления, фильтры",
    "Управление процессами: ps, top, kill, jobs, bg, fg",
    "Управление пакетами: apt, yum, dpkg, rpm",
    "Работа с текстом: grep, sed, awk, cut, sort",
    "Скриптинг на Bash: переменные, условия, циклы",
    "Файловые разрешения и владельцы: chmod, chown",
    "Сетевые утилиты: ping, netstat, ss, curl, wget",
    "Системные демоны и службы: systemd, journalctl",
    "Основы Git: init, commit, push, pull, merge",
    "Основы Docker: контейнеры, образы, Dockerfile",
    "Основы CI/CD: концепции, Jenkins, GitLab CI",
    "Основы облачных технологий: AWS/GCP/Azure",
    "Основы инфраструктуры как кода: Terraform",
    "Основы оркестрации: Kubernetes, Docker Swarm"
]

class StudyScheduler:
    def __init__(self):
        self.user_schedule = WORK_SCHEDULE
        self.study_topics = STUDY_TOPICS
        self.current_topic_index = 0
        self.user_settings = {
            'morning_study': True,
            'evening_study': False,
            'min_study_time': 30,
            'max_study_time': 120,
            'notifications': True
        }

    def get_available_time(self, date_str: str) -> List[Tuple[str, str]]:
        day_info = self.user_schedule.get(date_str, {})

        if day_info.get('type') == 'day_off':
            return day_info.get('available', [('09:00', '23:59')])

        elif day_info.get('type') == 'day_shift':
            work_start = datetime.strptime(day_info['work'][0], '%H:%M').time()
            travel_time = day_info.get('travel', 90)
            morning_start = datetime.strptime('05:00', '%H:%M').time()
            morning_end = (datetime.combine(datetime.today(), work_start) -
                           timedelta(minutes=travel_time)).time()

            if morning_start < morning_end:
                return [(morning_start.strftime('%H:%M'), morning_end.strftime('%H:%M'))]

        elif day_info.get('type') == 'night_shift':
            work_start = datetime.strptime(day_info['work'][0], '%H:%M').time()
            travel_time = day_info.get('travel', 90)
            evening_start = (datetime.combine(datetime.today(), work_start) -
                             timedelta(minutes=travel_time)).time()
            evening_end = datetime.strptime('23:59', '%H:%M').time()

            if evening_start < evening_end:
                return [(evening_start.strftime('%H:%M'), evening_end.strftime('%H:%M'))]

        return []

    def get_today_study_plan(self) -> str:
        today = datetime.now().strftime('%Y-%m-%d')
        available_time = self.get_available_time(today)

        if not available_time:
            return "Сегодня у вас нет свободного времени для обучения. Отдыхайте!"

        topic = self.study_topics[self.current_topic_index]
        self.current_topic_index = (self.current_topic_index + 1) % len(self.study_topics)

        plan = f"📚 План обучения на {today}:\n"
        plan += f"⏳ Доступное время: {', '.join([f'{s}-{e}' for s, e in available_time])}\n"
        plan += f"🎯 Тема: {topic}\n"
        plan += "🔹 Рекомендуемое время: 1-2 часа\n"
        plan += "🔹 Совет: Делайте перерывы каждые 25 минут (метод Pomodoro)\n"
        return plan

    def get_next_study_topic(self) -> str:
        topic = self.study_topics[self.current_topic_index]
        self.current_topic_index = (self.current_topic_index + 1) % len(self.study_topics)
        return topic

scheduler = StudyScheduler()

# === Команды ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Привет, {user.first_name}! 👋\n"
        "Я твой помощник в изучении Linux и DevOps.\n"
        "Я буду напоминать тебе о времени для обучения и предлагать темы.\n\n"
        "Доступные команды:\n"
        "/today - План на сегодня\n"
        "/next - Следующая тема для изучения\n"
        "/schedule - Посмотреть расписание\n"
        "/settings - Настройки уведомлений\n"
    )
    if update.effective_chat.id == ADMIN_ID:
        text += "\n⚙️ Админ-команды:\n/add_schedule - Добавить расписание\n"
    await update.message.reply_text(text)

async def today_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = scheduler.get_today_study_plan()
    await update.message.reply_text(plan)

async def next_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = scheduler.get_next_study_topic()
    await update.message.reply_text(f"Следующая тема для изучения:\n🎯 {topic}")

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule_text = "📅 Ваше текущее расписание:\n\n"
    for date, info in scheduler.user_schedule.items():
        schedule_text += f"📌 {date}: {info['type']}\n"
        if 'work' in info:
            schedule_text += f"   Работа: {info['work'][0]} - {info['work'][1]}\n"
        if 'available' in info:
            slots = ', '.join([f"{start}-{end}" for start, end in info['available']])
            schedule_text += f"   Доступно: {slots}\n"
        schedule_text += "\n"
    await update.message.reply_text(schedule_text)

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Утренние занятия", callback_data='morning_study')],
        [InlineKeyboardButton("Вечерние занятия", callback_data='evening_study')],
        [InlineKeyboardButton("Минимальное время", callback_data='min_time')],
        [InlineKeyboardButton("Максимальное время", callback_data='max_time')],
        [InlineKeyboardButton("Уведомления", callback_data='notifications')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    settings = scheduler.user_settings
    text = (
        "⚙️ Настройки обучения:\n\n"
        f"🔸 Утренние занятия: {'вкл' if settings['morning_study'] else 'выкл'}\n"
        f"🔸 Вечерние занятия: {'вкл' if settings['evening_study'] else 'выкл'}\n"
        f"🔸 Мин. время: {settings['min_study_time']} мин\n"
        f"🔸 Макс. время: {settings['max_study_time']} мин\n"
        f"🔸 Уведомления: {'вкл' if settings['notifications'] else 'выкл'}\n"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    settings = scheduler.user_settings

    if data == 'morning_study':
        settings['morning_study'] = not settings['morning_study']
    elif data == 'evening_study':
        settings['evening_study'] = not settings['evening_study']
    elif data == 'notifications':
        settings['notifications'] = not settings['notifications']

    await settings_menu(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Ошибка:", exc_info=context.error)
    if ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Ошибка: {context.error}")
        except Exception:
            pass

# === Запуск ===

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('today', today_plan))
    app.add_handler(CommandHandler('next', next_topic))
    app.add_handler(CommandHandler('schedule', show_schedule))
    app.add_handler(CommandHandler('settings', settings_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    print("✅ Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()