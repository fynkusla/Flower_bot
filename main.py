from telegram import (Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext)
from datetime import datetime, timedelta, time
import pytz
import sqlite3
import logging
import shutil
import os
from apscheduler.util import undefined

SAMARA_TIMEZONE = pytz.timezone('Europe/Samara')
ADMIN_PASSWORD = "1336"

# Включить ведение журнала
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для ConversationHandler Анкета
ASK_PHONE, MAIN_MENU, ADD_REASON, ADD_CUSTOM_REASON, ADD_DATE, ADD_WISHES, DELETE_RECORD, CONFIRM_ADD = range(8)

# Состояния для ConversationHandler Заказ
PHONE, OCCASION, BUDGET, CUSTOM_BUDGET, DATE_SELECTION, CLIENT_REQUESTS, POSTCARD, POSTCARD_TEXT, DELIVERY, DELIVERY_ADDRESS, RECIPIENT, RECIPIENT_CONTACT, CONFIRMATION = range(
    13)

# Основная клавиатура
main_keyboard = ReplyKeyboardMarkup(
    [['Календарь событий'], ['Оформить заказ'], ['Наше расположение'], ['О нас']],
    one_time_keyboard=True)


def facts_to_str(user_data):
    facts = [f'{key}: {value}' for key, value in user_data.items() if key not in ['admin_access', 'selected_event']]
    return "\n".join(facts)


def create_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Создание таблицы для пользователей
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        phone_number TEXT
    )
    ''')

    # Создание таблицы для записей
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        reason TEXT,
        date TEXT,
        wishes TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        link TEXT
    )
    """)

    # Добавляем изначальные события, если их еще нет
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        events = [
            ("8 марта", "08.03", "ссылка не задана"),
            ("День матери", "24.11", "ссылка не задана"),
            ("День учителя", "05.10", "ссылка не задана"),
            ("День Святого Валентина", "14.02", "ссылка не задана"),
            ("Выпускные", "28.06", "ссылка не задана"),
            ("Новый год", "31.12", "ссылка не задана"),
            ("День семьи", "08.06", "ссылка не задана"),
            ("День рождения", "не указан", "ссылка не задана"),
            ("Свадьба (Годовщина)", "не указан", "ссылка не задана")
        ]
        cursor.executemany("INSERT INTO events (name, date, link) VALUES (?, ?, ?)", events)

    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()


def start(update: Update, context: CallbackContext) -> int:
    # Завершаем текущий разговор, если он идет
    update.message.reply_text(
        """
        Добро пожаловать в цветочную мастерскую Кека!

🌸 Здесь вы можете заказать:
• Букеты на любое событие
• Цветы для дома, чтобы радовать себя
• Цветочные композиции для вашего заведения
• Свадебные букеты
• Декор и оформление любой сложности 
(украшение входной группы, фотозоны, мероприятия)

Для подписчиков действует скидка 10% на первый заказ!

💬 Как заказать?
• Составьте заявку через бота
• Напишите в личные сообщения
• Позвоните или напишите по номеру: +7 927 007 8846 
(WhatsApp, Viber, Telegram)

Режим работы: 9:00 - 21:00

Наш адрес: 
Самара, Осетинская 6

Наш миникорнер с готовыми товарами:
Самара, Южное шоссе 9, кофейня Pluma coffee
        """,
        reply_markup=main_keyboard
    )

    context.user_data.clear()
    return ConversationHandler.END


def info(update: Update, context: CallbackContext):
    update.message.reply_text(
        """
        🌸 КЕКА ЦВЕТЫ – это мастерская флористического искусства, где создаются утончённые цветочные композиции и букеты для ваших особых событий.
С удовольствием окажем Вам любую цветочную помощь!

Собираем композиции как в нашем фирменном стиле, так и по вашим референсам, с учётом всех нюансов.

Оказываем услуги как физ.лицам, так и юр.лицам, предоставляем все необходимые документы. 

💬 Подписывайтесь на наш [Telegram-канал](https://t.me/kekaflowers), чтобы первыми узнавать об акциях.

📸 Мы также ждём вас в [Instagram](https://www.instagram.com/keka__flowers) и [ВКонтакте](https://vk.com/keka_flowers) – здесь вы найдёте примеры наших работ и истории из жизни.

✨ Привносим красоту в вашу жизнь и рассказываем о культуре цветов!
        """,
        reply_markup=main_keyboard,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )


def geo(update: Update, context: CallbackContext):
    update.message.reply_text(
        """
        Наш магазин находится здесь:
📍 [Самара, Осетинская ул., 6](https://yandex.ru/maps/org/keka_tsvety/94042601867/?ll=50.075679%2C53.152078&z=16.17)

Часы работы:
🕒 Пн-Вс: 9:00 - 21:00

Посетите нас и наслаждайтесь красотой живых цветов!
        """,
        reply_markup=main_keyboard,
        parse_mode='Markdown'
    )


def get_phone_number(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number FROM users WHERE user_id = ?", (user_id,))
    phone_number = cursor.fetchone()
    conn.close()
    return phone_number[0] if phone_number else None


def save_phone_number(user_id, phone_number):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, phone_number) VALUES (?, ?)", (user_id, phone_number))
    conn.commit()
    conn.close()


def zakaz(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id

    # Проверяем наличие номера телефона в базе данных
    phone_number = get_phone_number(user_id)

    if phone_number:
        # Если номер найден, сохраняем его в user_data и продолжаем
        context.user_data['Телефон'] = phone_number
        return phone(update, context)  # Переходим к следующему состоянию
    else:
        # Если номера нет, запрашиваем его
        update.message.reply_text(
            '📞 Пожалуйста, поделитесь своим номером телефона, чтобы мы могли продолжить! Или нажмите "Пропустить", если хотите оставить этот шаг пустым. 😊',
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Отправить номер телефона", request_contact=True)], ['Пропустить']],
                one_time_keyboard=True
            )
        )
        return PHONE

def phone(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id

    if update.message.contact:
        contact = update.message.contact
        context.user_data['Телефон'] = contact.phone_number
        save_phone_number(user_id, contact.phone_number)  # Сохраняем номер в базе данных
    else:
        # Подключение к базе данных, чтобы получить номер телефона
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT phone_number FROM users WHERE user_id = ?", (user_id,))
            phone_number = cursor.fetchone()
            if phone_number:
                context.user_data['Телефон'] = phone_number[0]
            else:
                context.user_data['Телефон'] = 'Не указан'
        except Exception as e:
            print(f"Ошибка при получении номера телефона из базы данных: {e}")
            context.user_data['Телефон'] = 'Не указан'
        finally:
            conn.close()

    # Кнопки с поводами и возможностью указать свой
    occasion_keyboard = ReplyKeyboardMarkup(
        [['💍 Свадьба', '🎉 День рождения'],
         ['🌹 Юбилей', '❤️ Романтический подарок'],
         ['🏡 Цветы домой', '🎁 Без повода'],['🔙 Назад']],
        one_time_keyboard=True
    )

    update.message.reply_text(
        'Пожалуйста, выберите повод или напишите свой🤗',
        reply_markup=occasion_keyboard
    )
    return OCCASION

def occasion(update: Update, context: CallbackContext) -> int:
    if update.message.text != '🔙 Назад':
        context.user_data['Повод'] = update.message.text    # Отправляем пользователю выбор бюджета с изображениями
    update.message.reply_text(
        '''💐 Укажите сумму, чтобы мы могли предложить лучший вариант! 💸

⭐️C нашим ассортиментом вы можете ознакомиться перейдя по ссылке:
https://vk.com/keka_flowers
        ''',
        reply_markup=ReplyKeyboardMarkup(
            [['💎 от 5тыс', '💰 3-5тыс', '🪙 1-3тыс', '✏️ Указать свой'], ['🔙 Назад']],
            one_time_keyboard=True
        )
    )
    return BUDGET


def budget(update: Update, context: CallbackContext) -> int:
    selection = update.message.text
    if selection == '✏️ Указать свой':
        update.message.reply_text('''
        Пожалуйста, введите желаемый бюджет 
                                      ''')
        return CUSTOM_BUDGET
    else:
        context.user_data['Бюджет'] = selection
        return select_date(update, context)


def custom_budget(update: Update, context: CallbackContext) -> int:
    if update.message.text != '🔙 Назад':
        context.user_data['Бюджет'] = update.message.text
    return select_date(update, context)

def select_date(update: Update, context: CallbackContext) -> int:
    # Определяем даты на сегодня, завтра и послезавтра
    available_dates = [
        (datetime.now()).strftime('%d.%m'),  # Сегодня
        (datetime.now() + timedelta(days=1)).strftime('%d.%m'),  # Завтра
        (datetime.now() + timedelta(days=2)).strftime('%d.%m')  # Послезавтра
    ]

    # Добавляем кнопку для указания своей даты
    date_keyboard = ReplyKeyboardMarkup(
        [available_dates, ['✏️ Указать свою дату'],['🔙 Назад']],
        one_time_keyboard=True
    )

    update.message.reply_text(
        "📅 Укажите дату доставки:",
        reply_markup=date_keyboard
    )
    return DATE_SELECTION

def date_selection(update: Update, context: CallbackContext) -> int:
    selection = update.message.text

    # Функция для проверки правильности формата даты
    def validate_date_format(date_text):
        from datetime import datetime
        try:
            datetime.strptime(date_text, '%d.%m')
            return True
        except ValueError:
            return False

    if selection == '✏️ Указать свою дату':
        update.message.reply_text('Пожалуйста, введите желаемую дату в формате ДД.ММ:')
        return DATE_SELECTION  # Оставляем пользователя в состоянии выбора даты
    elif validate_date_format(selection):
        if update.message.text != '🔙 Назад':
            context.user_data['Дата'] = selection
        update.message.reply_text(
            '✨ Укажите название желаемой композиции (или отправьте ссылку на нее), а также свои пожелания к цветочному составу и цветовой гамме. 🌸',
            reply_markup=ReplyKeyboardMarkup([['🔙 Назад']], one_time_keyboard=True)
        )
        return CLIENT_REQUESTS
    else:
        update.message.reply_text('❗ Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.')
        return DATE_SELECTION

def client_requests(update: Update, context: CallbackContext) -> int:
    if update.message.text != '🔙 Назад':
        context.user_data['Пожелания'] = update.message.text

    # Спрашиваем нужна ли открытка
    update.message.reply_text(
        '📜 Хотите добавить открытку к букету? Это отличный способ выразить свои чувства! 💌',
        reply_markup=ReplyKeyboardMarkup([['Да', 'Нет'],['🔙 Назад']], one_time_keyboard=True)
    )

    return POSTCARD

def postcard(update: Update, context: CallbackContext) -> int:
    if update.message.text == 'Да':
        update.message.reply_text('🖊️ Пожалуйста, введите текст для открытки: 💕')
        return POSTCARD_TEXT
    else:
        return ask_delivery(update, context)

def postcard_text(update: Update, context: CallbackContext) -> int:
    if update.message.text != '🔙 Назад':
        context.user_data['Текст открытки'] = update.message.text
    return ask_delivery(update, context)

def ask_delivery(update: Update, context: CallbackContext) -> int:
    # Спрашиваем нужна ли доставка
    update.message.reply_text(
        '🚗 Нужна ли доставка букета? Мы доставим его по указанному адресу с заботой! 🏡',
        reply_markup=ReplyKeyboardMarkup([['Да', 'Нет'],['🔙 Назад']], one_time_keyboard=True)
    )
    return DELIVERY

def delivery(update: Update, context: CallbackContext) -> int:
    if update.message.text == 'Да':
        update.message.reply_text(
            '📍 Пожалуйста, укажите адрес (улица, дом, подъезд и квартира), куда нужно доставить букет: 🏠')
        return DELIVERY_ADDRESS
    else:
        return ask_recipient(update, context)

def delivery_address(update: Update, context: CallbackContext) -> int:
    if update.message.text != '🔙 Назад':
        context.user_data['Адрес доставки'] = update.message.text
    return ask_recipient(update, context)

def ask_recipient(update: Update, context: CallbackContext) -> int:
    # Спрашиваем, сам ли заказчик является получателем
    update.message.reply_text(
        '🎁 Получатель Вы? 😊',
        reply_markup=ReplyKeyboardMarkup([['Да', 'Нет'],['🔙 Назад']], one_time_keyboard=True)
    )
    return RECIPIENT

def recipient(update: Update, context: CallbackContext) -> int:
    if update.message.text == 'Нет':
        update.message.reply_text(
            '👤 Пожалуйста, укажите имя и телефон получателя: 📞')
        return RECIPIENT_CONTACT
    else:
        return confirmation(update, context)

def recipient_contact(update: Update, context: CallbackContext) -> int:
    if update.message.text != '🔙 Назад':
        context.user_data['Контакт получателя'] = update.message.text
    return confirmation(update, context)

def confirmation(update: Update, context: CallbackContext) -> int:
    # Отправляем запрос на подтверждение всех данных
    update.message.reply_text(
        f"🔍 Пожалуйста, проверьте введённую информацию, чтобы всё было правильно: ✅\n{facts_to_str(context.user_data)}",
        reply_markup=ReplyKeyboardMarkup([['Подтвердить', 'Отменить'],['🔙 Назад']], one_time_keyboard=True)
    )
    return CONFIRMATION


# Обработчик подтверждения
def confirmation_handler(update: Update, context: CallbackContext) -> int:
    if update.message.text == 'Подтвердить':
        # Отправляем сообщение менеджеру
        manager_chat_id = '@kkekrersd'
        context.bot.send_message(chat_id=manager_chat_id, text=f"Новая заявка:\n{facts_to_str(context.user_data)}")
        update.message.reply_text(
            '🎉 Спасибо! Ваша заявка успешно отправлена! 💐 \n📩 Мы свяжемся с вами в ближайшее время для подтверждения. 😊',
            reply_markup=main_keyboard)
        context.user_data.clear()
        return ConversationHandler.END
    else:
        update.message.reply_text(
            '❌ Заявка отменена.\n💭 Если передумаете, вы всегда можете вернуться и оформить новую заявку. 😊',
            reply_markup=main_keyboard)
        context.user_data.clear()
        return ConversationHandler.END

def back_occasion(update: Update, context: CallbackContext) -> int:
    del context.user_data['Повод']
    return phone(update, context)

def back_budget(update: Update, context: CallbackContext) -> int:
    del context.user_data['Бюджет']
    return occasion(update, context)

def back_date(update: Update, context: CallbackContext) -> int:
    del context.user_data['Дата']
    return select_date(update, context)

def back_requests(update: Update, context: CallbackContext) -> int:
    del context.user_data['Пожелания']
    return date_selection(update, context)

def back_postcard(update: Update, context: CallbackContext) -> int:
    if 'Текст открытки' in context.user_data and context.user_data['Текст открытки'] is not None:
        del context.user_data['Текст открытки']
    return client_requests(update, context)


def back_delivery(update: Update, context: CallbackContext) -> int:
    if 'Адрес доставки' in context.user_data and context.user_data['Адрес доставки'] is not None:
        del context.user_data['Адрес доставки']
    return ask_delivery(update, context)


def back_recipient(update: Update, context: CallbackContext) -> int:
    if 'Контакт получателя' in context.user_data and context.user_data['Контакт получателя'] is not None:
        del context.user_data['Контакт получателя']
    return ask_recipient(update, context)

# Функция начала, проверка пользователя
def anketa(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        # Запрос номера телефона
        keyboard = [[KeyboardButton("Отправить номер телефона", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        update.message.reply_text(
            "📞 Нажмите кнопку ниже, чтобы поделиться своим номером телефона. Это удобно и быстро! ☺️",
            reply_markup=reply_markup)
        return ASK_PHONE
    else:
        # Показать меню
        return show_main_menu(update, context)


# Получение номера телефона и сохранение в базу данных
def ask_phone(update: Update, context: CallbackContext) -> int:
    contact = update.message.contact
    user_id = update.message.from_user.id
    phone_number = contact.phone_number

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, phone_number) VALUES (?, ?)", (user_id, phone_number))
    conn.commit()
    conn.close()

    return show_main_menu(update, context)


# Показ главного меню
def show_main_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [['Добавить запись', 'Удалить запись'], ['Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("""
    "Календарь событий" 🌸

Поможет вам вовремя подготовиться к важным датам: дням рождения, годовщинам и другим праздникам.

✨ Как это работает?
1️⃣ Укажите повод праздника, дату и ваши пожелания.
2️⃣ За несколько дней до события мы пришлём вам напоминание, чтобы вы успели подготовиться и удивить близких.

💡 Секрет успеха: запишите все важные даты, и мы позаботимся, чтобы вы ничего не забыли! 🎈
📋 Выберите действие из меню ниже или нажмите 'Назад', чтобы вернуться в главное меню. 🙃
 """, reply_markup=reply_markup)

    user_id = update.message.from_user.id

    # Получение записей пользователя
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE user_id=?", (user_id,))
    records = cursor.fetchall()
    conn.close()

    if records:
        records_list = '\n'.join([f"{i + 1}. {rec[2]} ({rec[3]})" for i, rec in enumerate(records)])
        records_message = f"📋 Ваши записи:\n{records_list}\n\nВыберите действие из меню ниже: 😊"
    else:
        records_message = "📭 У вас пока нет записей. Создайте первую, чтобы начать! ✨"

    update.message.reply_text(records_message, reply_markup=reply_markup)

    return MAIN_MENU


# Обработка выбора из меню
def main_menu(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == 'Добавить запись':
        update.message.reply_text("Выберите на клавиатуре повод 😉", reply_markup=ReplyKeyboardMarkup(
            [['Свадьба (Годовщина)', 'День рождения', 'Другое']],
            one_time_keyboard=True))
        return ADD_REASON
    elif text == 'Удалить запись':
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        user_id = update.message.from_user.id
        cursor.execute("SELECT * FROM records WHERE user_id=?", (user_id,))
        records = cursor.fetchall()
        conn.close()

        if records:
            records_list = '\n'.join([f"{i + 1}. {rec[2]} ({rec[3]})" for i, rec in enumerate(records)])
            update.message.reply_text(
                f"🗑️ Ваши записи:\n{records_list}\n\nВведите номер записи, которую хотите удалить: ❌")
            return DELETE_RECORD
        else:
            update.message.reply_text("📭 У вас пока нет записей. Создайте первую, чтобы начать! ✨ ")
            return show_main_menu(update, context)
    elif text == 'Назад':
        update.message.reply_text("🔙 Возвращаемся в главное меню! 🌟")
        return start(update, context)
    else:
        update.message.reply_text("➡️ Пожалуйста, выберите вариант из меню ниже: 😊")
        return MAIN_MENU


# Добавление записи
def add_reason(update: Update, context: CallbackContext) -> int:
    # Создание клавиатуры для выбора повода
    keyboard = [['Свадьба (Годовщина)', 'День рождения'], ['Другое']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("🎉 Выберите повод для букета. Это поможет нам предложить что-то подходящее: 🌸",
                              reply_markup=reply_markup)
    return ADD_REASON


def process_reason(update: Update, context: CallbackContext) -> int:
    reason = update.message.text
    valid_reasons = ['Свадьба (Годовщина)', 'День рождения', 'Другое']

    if reason not in valid_reasons:
        update.message.reply_text("⚠️ Пожалуйста, выберите один из предложенных вариантов. Это важно для точности! ✅")
        return ADD_REASON

    if reason == 'Другое':
        # Предлагаем пользователю ввести свой повод
        update.message.reply_text("🎉 Пожалуйста, укажите ваш повод для заказа.")
        return ADD_CUSTOM_REASON  # Переход в состояние для ввода повода вручную

    # Если повод выбран из списка, сохраняем его
    context.user_data['reason'] = reason
    update.message.reply_text("📅 Введите дату (в формате ДД.ММ), чтобы мы знали, когда подготовить заказ: 🕒")
    return ADD_DATE


def process_custom_reason(update: Update, context: CallbackContext) -> int:
    custom_reason = update.message.text.strip()

    if not custom_reason:
        update.message.reply_text("🚫 Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ. 📆")
        return ADD_CUSTOM_REASON

    context.user_data['reason'] = custom_reason
    update.message.reply_text("📅 Введите дату (в формате ДД.ММ):")
    return ADD_DATE


def add_date(update: Update, context: CallbackContext) -> int:
    date = update.message.text
    # Проверка формата даты DD.MM
    if not validate_date_format(date):
        update.message.reply_text("🚫 Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ. 📆")
        return ADD_DATE

    context.user_data['date'] = date
    update.message.reply_text(
        "🌼 Здесь вы можете указать свои пожелания по цветам и цветовой гамме, чтобы мы сделали ваш букет особенным: ✨")
    return ADD_WISHES


def add_wishes(update: Update, context: CallbackContext) -> int:
    context.user_data['wishes'] = update.message.text
    reason = context.user_data['reason']
    date = context.user_data['date']
    wishes = context.user_data.get('wishes', '')

    # Создание клавиатуры с кнопками Подтвердить и Отменить
    keyboard = [[KeyboardButton("Подтвердить"), KeyboardButton("Отменить")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text(
        f"✅ Пожалуйста, подтвердите добавление записи:\nПовод: {reason}\nДата: {date}\nПожелания: {wishes}",
        reply_markup=reply_markup
    )
    return CONFIRM_ADD


def confirm_add(update: Update, context: CallbackContext) -> int:
    if update.message.text == "Подтвердить":
        user_id = update.message.from_user.id
        reason = context.user_data['reason']
        date = context.user_data['date']
        wishes = context.user_data.get('wishes', '')

        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO records (user_id, reason, date, wishes) VALUES (?, ?, ?, ?)",
                       (user_id, reason, date, wishes))
        conn.commit()
        conn.close()

        update.message.reply_text("🎉 Запись успешно добавлена. Спасибо! 🌟")
    else:
        update.message.reply_text("Добавление записи отменено.")
    context.user_data.clear()
    return show_main_menu(update, context)


def cancel_add(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Добавление записи отменено.")
    context.user_data.clear()
    return show_main_menu(update, context)


# Удаление записи
def delete_record(update: Update, context: CallbackContext) -> int:
    try:
        record_num = int(update.message.text) - 1
        user_id = update.message.from_user.id

        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records WHERE user_id=?", (user_id,))
        records = cursor.fetchall()

        if 0 <= record_num < len(records):
            record_id = records[record_num][0]
            cursor.execute("DELETE FROM records WHERE id=?", (record_id,))
            conn.commit()
            update.message.reply_text("🗑️ Запись успешно удалена!\nВозвращаем вас в главное меню. 😊")
        else:
            update.message.reply_text(
                "⚠️ Некорректный номер записи!\nПожалуйста, проверьте введённое значение и попробуйте снова. 😊")
        conn.close()
    except ValueError:
        update.message.reply_text(
            "🔢 Введите корректный номер записи:\nУбедитесь, что вы указали правильный номер из списка. 😊")

    return show_main_menu(update, context)


# Проверка формата даты (ДД.ММ)
def validate_date_format(date_text):
    from datetime import datetime
    try:
        datetime.strptime(date_text, '%d.%m')
        return True
    except ValueError:
        return False


# Обработчики команд
def cancel(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()  # Очистка данных пользователя
    update.message.reply_text('Заявка отменена.', reply_markup=main_keyboard)
    return ConversationHandler.END


def error(update: Update, context: CallbackContext) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    context.user_data.clear()  # Очистка данных пользователя при ошибке


def add_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def get_events():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    conn.close()
    return events


def update_event(event_id, date=None, link=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    if date:
        cursor.execute("UPDATE events SET date = ? WHERE id = ?", (date, event_id))
    if link:
        cursor.execute("UPDATE events SET link = ? WHERE id = ?", (link, event_id))
    conn.commit()
    conn.close()


# Функция для запроса пароля
def admin(update, context):
    update.message.reply_text("Введите пароль:")
    return 1


def check_password(update, context):
    password = update.message.text
    if password == ADMIN_PASSWORD:
        context.user_data['admin_access'] = True
        show_events(update, context)
        return 2
    else:
        update.message.reply_text("Неверный пароль, попробуйте снова или используйте /start для выхода.")
        return -1


def show_events(update, context):
    if not context.user_data.get('admin_access'):
        update.message.reply_text("У вас нет доступа. Введите команду /admin.")
        return -1

    # Формируем сообщение со списком праздников из базы данных
    events = get_events()
    events_text = "Список праздников:\n" + "\n".join(
        f"{event[0]}. {event[1]} - {event[2]} - {event[3]}" for event in events
    )
    reply_keyboard = [["Назад", "Изменить"]]
    update.message.reply_text(events_text, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
    return 2


def handle_button(update, context):
    text = update.message.text

    if text == "Назад":
        start(update, context)
        return -1
    elif text == "Изменить":
        update.message.reply_text("Введите номер праздника для изменения:")
        return 3


def select_event(update, context):
    text = update.message.text

    # Проверяем, нажал ли пользователь "Назад"
    if text == "Назад":
        show_events(update, context)
        return 2

    try:
        # Пробуем преобразовать текст в номер события
        event_number = int(text)
        events = get_events()

        # Проверяем, что введенный номер находится в диапазоне
        if event_number < 1 or event_number > len(events):
            update.message.reply_text("Неправильный номер. Попробуйте снова.")
            return 3

        # Сохраняем ID выбранного события и показываем опции изменения
        context.user_data['selected_event'] = events[event_number - 1][0]  # Сохраняем ID события
        reply_keyboard = [["Назад", "Изменить Дату", "Изменить Ссылку"]]
        update.message.reply_text(
            f"Выбранный праздник: {events[event_number - 1][1]}",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
        )
        return 4
    except ValueError:
        update.message.reply_text("Введите корректный номер праздника.")
        return 3


def edit_event_option(update, context):
    text = update.message.text
    selected_event = context.user_data.get('selected_event')

    if text == "Назад":
        show_events(update, context)
        return 2
    elif text == "Изменить Дату":
        update.message.reply_text("Введите новую дату:")
        return 5
    elif text == "Изменить Ссылку":
        update.message.reply_text("Введите новую ссылку:")
        return 6


def set_event_date(update, context):
    selected_event = context.user_data.get('selected_event')
    new_date = update.message.text
    update_event(selected_event, date=new_date)
    update.message.reply_text("Дата обновлена.")
    show_events(update, context)
    return 2


def set_event_link(update, context):
    selected_event = context.user_data.get('selected_event')
    new_link = update.message.text
    update_event(selected_event, link=new_link)
    update.message.reply_text("Ссылка обновлена.")
    show_events(update, context)
    return 2


def cancel(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()  # Очистка данных пользователя
    update.message.reply_text('Заявка отменена.', reply_markup=main_keyboard)
    return ConversationHandler.END


def convert_date_to_month_day_format(iso_date: datetime.date) -> str:
    return iso_date.strftime("%d.%m")


# Функция для пересылки сообщений

def broadcast_forward_message(context, from_chat_id, link, user_ids):
    for user_id in user_ids:
        try:
            context.bot.forward_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=link)
        except Exception as e:
            print(f"Ошибка при пересылке сообщения пользователю {user_id}: {e}")


# Функция для проверки и рассылки событий о предстоящих праздниках
def check_and_broadcast_events(context: CallbackContext):
    today = datetime.now(SAMARA_TIMEZONE).date()
    today_month_day = convert_date_to_month_day_format(today)
    date_in_one_day = convert_date_to_month_day_format(today + timedelta(days=1))
    date_in_three_days = convert_date_to_month_day_format(today + timedelta(days=3))
    date_in_five_days = convert_date_to_month_day_format(today + timedelta(days=5))  # Новый интервал

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    try:
        cursor.execute(""" 
            SELECT date, link 
            FROM events 
            WHERE date IN (?, ?, ?, ?) 
        """, (today_month_day, date_in_one_day, date_in_three_days, date_in_five_days))

        events = cursor.fetchall()

        if not events:
            return

        cursor.execute("SELECT user_id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]

        if not user_ids:
            return

        for db_date, link in events:
            broadcast_forward_message(context, from_chat_id='@kekaflowers', link=link, user_ids=user_ids)

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        conn.close()


# Функция для проверки и рассылки личных событий пользователей
def check_and_broadcast_user_events(context: CallbackContext):
    today = datetime.now(SAMARA_TIMEZONE).date()
    date_in_one_day = today + timedelta(days=1)
    date_in_three_days = today + timedelta(days=3)
    date_in_seven_days = today + timedelta(days=7)  # Новый интервал

    today_month_day = convert_date_to_month_day_format(today)
    date_in_one_day_month_day = convert_date_to_month_day_format(date_in_one_day)
    date_in_three_days_month_day = convert_date_to_month_day_format(date_in_three_days)
    date_in_seven_days_month_day = convert_date_to_month_day_format(date_in_seven_days)  # Новый формат

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    try:
        cursor.execute(""" 
            SELECT user_id, reason 
            FROM records 
            WHERE date IN (?, ?, ?, ?)
        """, (today_month_day, date_in_one_day_month_day, date_in_three_days_month_day, date_in_seven_days_month_day))

        user_records = cursor.fetchall()

        if not user_records:
            return

        for user_id, reason in user_records:
            cursor.execute("SELECT link FROM events WHERE name = ?", (reason,))
            event = cursor.fetchone()
            if event:
                link = event[0]
                broadcast_forward_message(context, from_chat_id='@kekaflowers', link=link, user_ids=[user_id])
    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        conn.close()


# Функция для создания бэкапа базы данных
def backup_database():
    db_file = 'bot_database.db'
    backup_file = f'bot_database_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

    try:
        shutil.copy(db_file, backup_file)
        return backup_file
    except Exception as e:
        print(f"Ошибка при создании бэкапа базы данных: {e}")
        return None


# Функция для отправки бэкапа пользователю
def send_backup_to_user(context: CallbackContext):
    user_id = 330121435
    backup_file = backup_database()

    if backup_file:
        try:
            with open(backup_file, 'rb') as file:
                context.bot.send_document(chat_id=user_id, document=file, filename=backup_file)
            os.remove(backup_file)  # Удаляем файл после отправки
        except Exception as e:
            print(f"Ошибка при отправке бэкапа пользователю: {e}")
    else:
        print("Не удалось создать бэкап базы данных.")


# Планирование задач
def schedule_tasks(updater: Updater):
    job_queue = updater.job_queue
    samara_time = time(9, 0, tzinfo=SAMARA_TIMEZONE)

    # Запуск задачи для бэкапа базы данных и отправки его пользователю
    job_queue.run_daily(send_backup_to_user, time=samara_time)
    job_queue.run_daily(check_and_broadcast_events, time=samara_time)
    job_queue.run_daily(check_and_broadcast_user_events, time=samara_time)


def main():
    create_database()
    updater = Updater("7786701773:AAES6hOSansnbEMPfQHlfJV0zKcawsB1EjM", use_context=True)
    dp = updater.dispatcher

    schedule_tasks(updater)
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.regex('Наше расположение'), geo))
    dp.add_handler(MessageHandler(Filters.regex('О нас'), info))

    conv_handler_zakaz = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('Оформить заказ'), zakaz)],
        states={
            PHONE: [
                MessageHandler(Filters.regex('🔙 Назад'), start),
                MessageHandler(Filters.contact, phone),
                MessageHandler(Filters.regex('Пропустить'), phone)
            ],
            OCCASION: [
                MessageHandler(Filters.regex('🔙 Назад'), start),
                MessageHandler(Filters.text & ~Filters.command, occasion)
            ],
            BUDGET: [
                MessageHandler(Filters.regex('🔙 Назад'), back_occasion),
                MessageHandler(Filters.regex('^(💎 от 5тыс|💰 3-5тыс|🪙 1-3тыс|✏️ Указать свой)$'), budget)
            ],
            CUSTOM_BUDGET: [
                MessageHandler(Filters.text & ~Filters.command, custom_budget)
            ],
            DATE_SELECTION: [
                MessageHandler(Filters.regex('🔙 Назад'), back_budget),
                MessageHandler(Filters.text & ~Filters.command, date_selection)
            ],
            CLIENT_REQUESTS: [
                MessageHandler(Filters.regex('🔙 Назад'), back_date),
                MessageHandler(Filters.text & ~Filters.command, client_requests)
            ],
            POSTCARD: [
                MessageHandler(Filters.regex('🔙 Назад'), back_requests),
                MessageHandler(Filters.regex('^(Да|Нет)$'), postcard)
            ],
            POSTCARD_TEXT: [
                MessageHandler(Filters.text & ~Filters.command, postcard_text)
            ],
            DELIVERY: [
                MessageHandler(Filters.regex('🔙 Назад'), back_postcard),
                MessageHandler(Filters.regex('^(Да|Нет)$'), delivery)
            ],
            DELIVERY_ADDRESS: [
                MessageHandler(Filters.text & ~Filters.command, delivery_address)
            ],
            RECIPIENT: [
                MessageHandler(Filters.regex('🔙 Назад'), back_delivery),
                MessageHandler(Filters.regex('^(Да|Нет)$'), recipient)
            ],
            RECIPIENT_CONTACT: [
                MessageHandler(Filters.text & ~Filters.command, recipient_contact)
            ],
            CONFIRMATION: [
                MessageHandler(Filters.regex('🔙 Назад'), back_recipient),
                MessageHandler(Filters.regex('^(Подтвердить|Отменить)$'), confirmation_handler)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', cancel),
                   (MessageHandler(Filters.regex('Оформить заказ'), zakaz))]  # Включаем отмену и начало
    )

    # Обработчик для всего процесса анкеты
    conversation_handler_anketa = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('Календарь событий'), anketa)],
        states={
            ASK_PHONE: [MessageHandler(Filters.contact, ask_phone)],
            MAIN_MENU: [MessageHandler(Filters.text, main_menu)],
            ADD_REASON: [MessageHandler(Filters.text & ~Filters.command, process_reason)],
            ADD_CUSTOM_REASON: [MessageHandler(Filters.text & ~Filters.command, process_custom_reason)],
            ADD_DATE: [MessageHandler(Filters.text & ~Filters.command, add_date)],
            ADD_WISHES: [MessageHandler(Filters.text & ~Filters.command, add_wishes)],
            CONFIRM_ADD: [MessageHandler(Filters.text & ~Filters.command, confirm_add)],
            DELETE_RECORD: [MessageHandler(Filters.text & ~Filters.command, delete_record)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', cancel),
                   (MessageHandler(Filters.regex('Календарь событий'), anketa)),
                   MessageHandler(Filters.regex('Назад'), start)]
    )

    conv_handler_admin = ConversationHandler(
        entry_points=[CommandHandler('admin', admin)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, check_password)],
            2: [MessageHandler(Filters.text & ~Filters.command, handle_button)],
            3: [MessageHandler(Filters.text & ~Filters.command, select_event)],
            4: [MessageHandler(Filters.text & ~Filters.command, edit_event_option)],
            5: [MessageHandler(Filters.text & ~Filters.command, set_event_date)],
            6: [MessageHandler(Filters.text & ~Filters.command, set_event_link)]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', cancel), CommandHandler('admin', cancel)]
    )

    dp.add_handler(conv_handler_admin)
    dp.add_handler(conv_handler_zakaz)
    dp.add_handler(conversation_handler_anketa)
    dp.add_error_handler(error)

    # Запуск бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()