from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime
from pytz import timezone
import asyncio
import nest_asyncio
import json
import os
import random
import re



# Установка часового пояса
custom_tz = timezone("Asia/Yekaterinburg")

# ID администратора
ADMIN_ID = 5036062193  # Замените на ваш реальный Telegram ID

# Файлы для хранения данных
SUBSCRIBED_USERS_FILE = "subscribed_chats.json"
SCHEDULE_FILE = "schedule.json"

# Перевод на русский
RU_DAYS = {
    "monday": "ПН",
    "tuesday": "ВТ",
    "wednesday": "СР",
    "thursday": "ЧТ",
    "friday": "ПТ",
    "saturday": "СБ",
    "sunday": "ВС",
}
RU_NOTIFICATION_TYPES = {
    'daily': 'Ежедневно',
    'weekly': 'Еженедельно',
    'biweekly_odd': 'Нечётные недели',
    'biweekly_even': 'Чётные недели',
}

# Загрузка подписанных пользователей из файла
def load_subscribed_users():
    try:
        with open("subscribed_chats.json", "r") as f:
            data = json.load(f)
            subscribed_users = data.get("subscribed_chats", [])
            return subscribed_users
    except FileNotFoundError:
        print("Файл 'subscribed_chats.json' не найден. Создаю новый список.")  # Отладка
        return []

# Сохранение подписанных пользователей в файл
def save_subscribed_users(subscribed_users):
    with open(SUBSCRIBED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"subscribed_chats": subscribed_users}, f)

# Загрузка расписания из файла
def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Сохранение расписания в файл
def save_schedule(schedule):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=4)

# Загрузка подписанных пользователей и расписания при старте бота
async def on_startup(application):
    # Загружаем подписанных пользователей
    subscribed_chats = load_subscribed_users()
    # Загружаем расписание
    schedule = load_schedule()

    # Отправляем сообщения сразу при запуске
    await send_scheduled_messages_immediately(application, subscribed_chats, schedule)


# Задача для отправки сообщений по расписанию
# Функция отправки сообщений по расписанию
async def send_scheduled_messages(application):
    # Загружаем подписанных пользователей
    subscribed_chats = load_subscribed_users()
    while True:
        now = datetime.now(custom_tz)
        current_day = now.strftime('%A').lower()
        current_time = now.strftime('%H:%M')
        current_week = now.isocalendar()[1]  # Получаем номер недели по ISO-календарю
        current_day_of_month = now.day  # Получаем день месяца для ежемесячных напоминаний
        formatted_day_of_month = f"day_{current_day_of_month:02d}"  # Форматируем день месяца с ведущим нулем, если нужно

        # Загружаем расписание
        schedule = load_schedule()

        # Основное расписание (ежедневные)
        if "daily" in schedule:
            for time, message in schedule["daily"].items():
                if time == current_time:
                    for chat_id in subscribed_chats:  # Используем загруженные chat_id
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=message)
                        except Exception as e:
                            pass  # Ошибка при отправке сообщения можно обработать, если нужно

        # Еженедельные напоминания
        if "weekly" in schedule:
            if current_day in schedule["weekly"]:
                for time, message in schedule["weekly"][current_day].items():
                    if time == current_time:
                        for chat_id in subscribed_chats:  # Используем загруженные chat_id
                            try:
                                await application.bot.send_message(chat_id=chat_id, text=message)
                            except Exception as e:
                                pass  # Ошибка при отправке сообщения можно обработать, если нужно

        # Нечётные недели
        biweekly_odd_key = f"biweekly_odd_{current_day}"
        if biweekly_odd_key in schedule:
            if current_week % 2 == 1:  # Нечётная неделя (по ISO-номеру недели)
                for time, message in schedule[biweekly_odd_key].items():
                    if time == current_time:
                        for chat_id in subscribed_chats:  # Используем загруженные chat_id
                            try:
                                await application.bot.send_message(chat_id=chat_id, text=message)
                            except Exception as e:
                                pass  # Ошибка при отправке сообщения можно обработать, если нужно

        # Чётные недели
        biweekly_even_key = f"biweekly_even_{current_day}"
        if biweekly_even_key in schedule:
            if current_week % 2 == 0:  # Чётная неделя (по ISO-номеру недели)
                for time, message in schedule[biweekly_even_key].items():
                    if time == current_time:
                        for chat_id in subscribed_chats:  # Используем загруженные chat_id
                            try:
                                await application.bot.send_message(chat_id=chat_id, text=message)
                            except Exception as e:
                                pass  # Ошибка при отправке сообщения можно обработать, если нужно

        # Ежемесячные напоминания
        if "monthly" in schedule:
            if formatted_day_of_month in schedule["monthly"]:
                for time, message in schedule["monthly"][formatted_day_of_month].items():
                    if time == current_time:
                        for chat_id in subscribed_chats:  # Используем загруженные chat_id
                            try:
                                await application.bot.send_message(chat_id=chat_id, text=message)
                            except Exception as e:
                                pass  # Ошибка при отправке сообщения можно обработать, если нужно

        # Ожидание 1 минуты перед следующей проверкой
        await asyncio.sleep(60)

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed_chats = context.application.bot_data.setdefault("subscribed_chats", load_subscribed_users())

    if chat_id not in subscribed_chats:
        subscribed_chats.append(chat_id)
        save_subscribed_users(subscribed_chats)  # Сохраняем в файл
        await update.message.reply_text("Привет! Я бот-напоминалка. Я буду отправлять сообщения согласно расписанию.")
    else:
        reply = await get_random_reply_from_file()
        await update.message.reply_text(reply)

# Получение случайного ответа из файла
async def get_random_reply_from_file(file_path="jokes.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            replies = f.readlines()
        return random.choice(replies).strip()
    except FileNotFoundError:
        return "❗Ответы не найдены. Добавьте файл jokes.txt с ответами."

# Обработка команды /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribed_chats = context.application.bot_data.setdefault("subscribed_chats", load_subscribed_users())

    if chat_id in subscribed_chats:
        subscribed_chats.remove(chat_id)
        save_subscribed_users(subscribed_chats)  # Сохраняем изменения
        await update.message.reply_text("Вы отписались от уведомлений.")
    else:
        await update.message.reply_text("Вы не были подписаны.")

# Обработка команды /now
async def now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(custom_tz)
    current_time = now.strftime('%H:%M')
    current_day = now.strftime('%A').lower()
    current_week = now.isocalendar()[1]  # Получаем номер недели по ISO-календарю

    current_day_ru = RU_DAYS.get(current_day, current_day).capitalize()
    week_type = "чётная" if current_week % 2 == 0 else "нечётная"

    response = f"🕒Текущее время: {current_time}\n📅День недели: {current_day_ru}\n🗓️Четность недели: {week_type}"
    await update.message.reply_text(response)

# Обработка команды /next
async def next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(custom_tz)
    current_day = now.strftime('%A').lower()
    current_time = now.strftime('%H:%M')
    current_week = int(now.strftime('%U'))
    current_month = now.month
    current_day_of_month = now.day

    schedule = load_schedule()
    next_message = None
    next_time_diff = None

    # Функция для определения разницы по времени
    def time_diff(time_str):
        time_obj = datetime.strptime(time_str, '%H:%M')
        current_time_obj = datetime.strptime(current_time, '%H:%M')
        return (time_obj - current_time_obj).total_seconds()

    # Проверка на ежедневные напоминания
    if "daily" in schedule:
        for time, task in schedule["daily"].items():
            diff = time_diff(time)
            if diff > 0 and (next_time_diff is None or diff < next_time_diff):
                next_message = f"🔔Следующее напоминание (ежедневно): {task} в {time}"
                next_time_diff = diff

    # Проверка на еженедельные напоминания
    if "weekly" in schedule:
        for day, tasks in schedule["weekly"].items():
            if day == current_day:
                for time, task in tasks.items():
                    diff = time_diff(time)
                    if diff > 0 and (next_time_diff is None or diff < next_time_diff):
                        next_message = f"🔔Следующее напоминание (еженедельно): {task} в {time} (на {RU_DAYS.get(day, day).capitalize()})"
                        next_time_diff = diff

    # Проверка на напоминания для нечетных недель
    if "biweekly_odd" in schedule and (current_week % 2 == 1):
        for day, tasks in schedule["biweekly_odd"].items():
            if day == current_day:
                for time, task in tasks.items():
                    diff = time_diff(time)
                    if diff > 0 and (next_time_diff is None or diff < next_time_diff):
                        next_message = f"🔔Следующее напоминание (нечетные недели): {task} в {time} (на {RU_DAYS.get(day, day).capitalize()})"
                        next_time_diff = diff

    # Проверка на напоминания для четных недель
    if "biweekly_even" in schedule and (current_week % 2 == 0):
        for day, tasks in schedule["biweekly_even"].items():
            if day == current_day:
                for time, task in tasks.items():
                    diff = time_diff(time)
                    if diff > 0 and (next_time_diff is None or diff < next_time_diff):
                        next_message = f"🔔Следующее напоминание (четные недели): {task} в {time} (на {RU_DAYS.get(day, day).capitalize()})"
                        next_time_diff = diff

    # Проверка на ежемесячные напоминания
    if "monthly" in schedule:
        for day_key, tasks in schedule["monthly"].items():
            day_of_month = int(day_key.split('_')[1])
            if day_of_month >= current_day_of_month:
                for time, task in tasks.items():
                    diff = time_diff(time)
                    if diff > 0 and (next_time_diff is None or diff < next_time_diff):
                        next_message = f"🔔Следующее напоминание (ежемесячно): {task} в {time} (на {day_of_month}-е число)"
                        next_time_diff = diff

    if next_message:
        await update.message.reply_text(next_message)
    else:
        await update.message.reply_text("❗Следующее напоминание на сегодня не найдено.")

def format_schedule(schedule):
    message = "📅 Текущее расписание (Время МСК+2):\n\n"
    schedule = load_schedule()
    # Ежедневные события
    message += "🗓 Ежедневно:\n"
    for time, task in schedule["daily"].items():
        message += f"  ⏰ {time} — {task}\n"

    # Еженедельные события
    message += "\n🗓 Еженедельно:\n"
    for day, tasks in schedule["weekly"].items():
        for time, task in tasks.items():
            message += f"  ⏰ {RU_DAYS.get(day)} — {time} — {task}\n"

    # Чётные недели
    message += "\n🗓 Чётные недели:\n"
    for day, tasks in schedule["biweekly_even"].items():
        for time, task in tasks.items():
            message += f"  ⏰ {RU_DAYS.get(day)} — {time} — {task}\n"

    # Нечётные недели
    message += "\n🗓 Нечётные недели:\n"
    for day, tasks in schedule["biweekly_odd"].items():
        for time, task in tasks.items():
            message += f"  ⏰ {RU_DAYS.get(day)} — {time} — {task}\n"

    # Ежемесячные события
    message += "\n🗓 Ежемесячно:\n"
    for day, tasks in schedule["monthly"].items():
        # Заменим day_x на "День X"
        if day.startswith("day_"):
            day_number = day.split("_")[1]  # Получаем число после "day_"
            day = f"День {day_number}"  # Форматируем как "День X"
        for time, task in tasks.items():
            message += f"  ⏰ {day} — {time} — {task}\n"

    # Завершение
    message += "\n💬 *Это текущее расписание для всех типов уведомлений.*"

    return message

# Обработка команды удаления уведомлений
async def delete_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для удаления уведомлений."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для удаления уведомлений.")
        return

    # Сбрасываем режим добавления, если он был включён
    context.user_data.clear()
    context.user_data["delete_mode"] = True  # Включаем режим удаления

    schedule = load_schedule()
    notifications = []
    index_map = {}

    idx = 1
    for type_key, days in schedule.items():
        if not isinstance(days, dict):
            continue
        for day, tasks in days.items():
            if not isinstance(tasks, dict):
                continue
            for time, task in tasks.items():
                notifications.append(f"{idx}. [{RU_NOTIFICATION_TYPES.get(type_key, type_key)}] {RU_DAYS.get(day, day)} - {time}: {task}")
                index_map[idx] = (type_key, day, time)
                idx += 1

    if notifications:
        message_text = "📋 Список уведомлений:\n\n" + "\n".join(notifications)
        message_text += "\n\nВведите номер уведомления для удаления."
        context.user_data["index_map"] = index_map
        await update.message.reply_text(message_text)
    else:
        await update.message.reply_text("❗ Уведомлений нет.")

# Обработка ввода номера уведомления
async def handle_delete_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора номера для удаления."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для удаления уведомлений.")
        return

    if not context.user_data.get("delete_mode"):
        return  # Если не в режиме удаления, выходим

    try:
        notification_number = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❗ Введите корректный номер уведомления.")
        return

    index_map = context.user_data.get("index_map", {})
    if notification_number not in index_map:
        await update.message.reply_text("❗ Уведомление с таким номером не найдено.")
        return

    type_key, day, time = index_map[notification_number]
    schedule = load_schedule()

    # Удаляем уведомление
    del schedule[type_key][day][time]
    if not schedule[type_key][day]:
        del schedule[type_key][day]
    if not schedule[type_key]:
        del schedule[type_key]

    save_schedule(schedule)

    await update.message.reply_text(f"✅ Уведомление удалено: {RU_DAYS.get(day, day)} - {time}")

    # Очищаем режим удаления
    context.user_data.clear()


# Функция для отправки расписания в чат
async def show_schedule(update: Update, context):
    schedule = load_schedule()
    formatted_schedule = format_schedule(schedule)
    await update.message.reply_text(formatted_schedule)


# Функция для проверки времени
def is_valid_time(time_str: str) -> bool:
    pattern = r'^[0-2][0-9]:[0-5][0-9]$'  # проверка формата ЧЧ:ММ
    return bool(re.match(pattern, time_str))

# Обработка команды добавления уведомления
async def add_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления уведомления."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для добавления расписания.")
        return

    # Сбрасываем режим удаления, если он был включён
    context.user_data.clear()
    context.user_data["add_mode"] = True  # Включаем режим добавления

    keyboard = [
        [InlineKeyboardButton("Ежедневное", callback_data="daily")],
        [InlineKeyboardButton("Еженедельное", callback_data="weekly")],
        [InlineKeyboardButton("Чётные недели", callback_data="biweekly_even")],
        [InlineKeyboardButton("Нечётные недели", callback_data="biweekly_odd")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите тип уведомления:", reply_markup=reply_markup)

# Обработка выбора типа уведомления
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_type = query.data

    if selected_type in ["daily", "weekly", "biweekly_even", "biweekly_odd"]:
        context.user_data["selected_type"] = selected_type  # Сохраняем тип уведомления

        if selected_type == "daily":
            await query.edit_message_text(text="Вы выбрали ежедневное уведомление. Укажите время в формате ЧЧ:ММ.")
        elif selected_type in ["weekly", "biweekly_even", "biweekly_odd"]:
            # Для еженедельных или двунедельных уведомлений показываем дни
            keyboard = [
                [InlineKeyboardButton(RU_DAYS[day].capitalize(), callback_data=day) for day in RU_DAYS.keys()]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Выберите день недели:", reply_markup=reply_markup)
    else:
        # Сохранение дня недели
        selected_day = query.data
        context.user_data["selected_day"] = selected_day

        await query.edit_message_text(text=f"Вы выбрали день: {RU_DAYS.get(selected_day, selected_day).capitalize()}. Теперь введите время уведомления в формате ЧЧ:ММ.")

async def day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_day = query.data  # день недели, выбранный пользователем
    context.user_data["selected_day"] = selected_day  # Сохраняем день недели

    # Попросим пользователя ввести время уведомления
    await query.edit_message_text(text=f"Вы выбрали день: {RU_DAYS.get(selected_day, selected_day).capitalize()}. Теперь введите время уведомления в формате ЧЧ:ММ.")

# Обработка текста для добавления уведомления
async def add_time_and_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    user_data = context.user_data
    selected_type = user_data.get("selected_type")

    if not selected_type:
        await update.message.reply_text("Тип уведомления не выбран.")
        return

    if selected_type == "daily":
        if "time" not in user_data:
            time = update.message.text
            if not is_valid_time(time):
                await update.message.reply_text("Время указано в неверном формате. Используйте формат ЧЧ:ММ.")
                return

            user_data["time"] = time
            await update.message.reply_text("Введите описание задачи:")
        elif "time" in user_data and "task" not in user_data:
            task = update.message.text
            time = user_data["time"]

            # Сохранение расписания
            schedule = load_schedule()
            schedule.setdefault("daily", {})[time] = task
            save_schedule(schedule)

            await update.message.reply_text(f"Добавлено: ежедневное уведомление в {time} - {task}")

            # Очистка данных пользователя
            user_data.clear()

    elif selected_type in ["weekly", "biweekly_odd", "biweekly_even"]:
        if "selected_day" not in user_data:
            await update.message.reply_text("Выберите день недели.")
            return

        selected_day = user_data["selected_day"]

        if "time" not in user_data:
            time = update.message.text
            if not is_valid_time(time):
                await update.message.reply_text("❗Время указано в неверном формате. Используйте формат ЧЧ:ММ.")
                return

            user_data["time"] = time
            await update.message.reply_text("Введите описание задачи:")
        elif "time" in user_data and "task" not in user_data:
            task = update.message.text
            time = user_data["time"]

            # Сохранение расписания с типом уведомления и днем недели
            schedule = load_schedule()

            # Для weekly, biweekly_odd, biweekly_even сохраняем задачу в соответствующий день
            if selected_type == "weekly":
                schedule.setdefault(f"weekly", {}).setdefault(selected_day, {})[time] = task
            elif selected_type == "biweekly_odd":
                schedule.setdefault(f"biweekly_odd", {}).setdefault(selected_day, {})[time] = task
            elif selected_type == "biweekly_even":
                schedule.setdefault(f"biweekly_even", {}).setdefault(selected_day, {})[time] = task

            save_schedule(schedule)

            await update.message.reply_text(f"Добавлено: {RU_DAYS.get(selected_day, selected_day).capitalize()}, {time} - {task}")

            # Очистка данных пользователя
            user_data.clear()




# Запуск бота
async def run_bot():
    nest_asyncio.apply()  # Устранение проблем с активным циклом событий

    token = "7949312036:AAEXXr4n_BBDjqtLjD7RuaYJ1P_FGod-v7A"  # Замените на ваш токен
    application = ApplicationBuilder().token(token).read_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("schedule", show_schedule))
    application.add_handler(CommandHandler("add", add_schedule))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("next", next))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("delete", delete_schedule))  # Команда для удаления
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_input))  # Обработка ввода номера
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_time_and_task))

    # Запуск задач
    asyncio.create_task(send_scheduled_messages(application))

    print("Бот запущен!")
    await application.run_polling(timeout=60)

# Запуск бота с учетом активного цикла событий
if __name__ == '__main__':
    asyncio.run(run_bot())
