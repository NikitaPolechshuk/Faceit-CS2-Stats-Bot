import os
import sqlite3
import tempfile

import telebot
from dotenv import load_dotenv

import constants
from logger import get_logger
from utils import download_page, generate_player_card, parse_faceitanalyser

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH")

logger = get_logger(__name__)

logger.info("----- Проверка .env -----")
if not BOT_TOKEN:
    logger.critical(constants.TOKEN_ENV_ERROR)
    raise ValueError(constants.TOKEN_ENV_ERROR)
if not DB_PATH:
    logger.critical(constants.DB_ENV_ERROR)
    raise ValueError(constants.DB_ENV_ERROR)


# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для временного хранения данных пользователей
user_registration_data = {}


def get_html_page_by_nickname(nickname):
    url = f"https://faceitanalyser.com/stats/{nickname}/cs2"
    return download_page(url)


def get_user_stat(nickname):
    faceitanalyser_html = get_html_page_by_nickname(nickname)
    return parse_faceitanalyser(faceitanalyser_html)


def get_faceit_nickname_from_db(telegram_id):
    """
    Получает никнейм Faceit из базы данных по telegram_id
    с обработкой ошибок
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT faceit_nickname FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )

        result = cursor.fetchone()
        if result:
            logger.info(f"Найден никнейм для {telegram_id}: {result[0]}")
            return result[0]
        else:
            logger.info(f"Пользователь с {telegram_id} не найден в БД")
            return None

    except sqlite3.Error as e:
        logger.error(f" Ошибка БД при получении никнейма: {e}")
        return None
    finally:
        if conn:
            conn.close()


def register_user(telegram_id, faceit_nickname):
    """
    Регистрирует или обновляет пользователя в базе данных
    Возвращает (успех, сообщение)
    """
    # Проверяем существование пользователя на Faceit
    user_stats = get_user_stat(faceit_nickname)
    if user_stats is None:
        logger.info(f"Пользователь {faceit_nickname} нет на Faceit")
        return None

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Проверяем существует ли пользователь
        cursor.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            # Обновляем существующего пользователя
            cursor.execute(
                """UPDATE users
                   SET faceit_nickname = ?, registered_at = CURRENT_TIMESTAMP
                   WHERE telegram_id = ?""",
                (faceit_nickname, telegram_id)
            )
            logger.info(f"Обновлен пользователь {telegram_id}: "
                        f"{faceit_nickname}")

        else:
            # Добавляем нового пользователя
            cursor.execute(
                """INSERT INTO users (telegram_id, faceit_nickname)
                   VALUES (?, ?)""",
                (telegram_id, faceit_nickname)
            )
            logger.info(f"Зарегистрирован пользователь {telegram_id}: "
                        f"{faceit_nickname}")

        conn.commit()
        return user_stats

    except sqlite3.Error as e:
        logger.error(f"Ошибка базы данных: {e}")
        return None
    finally:
        if conn:
            conn.close()


def send_high_quality_photo(chat_id, image, caption=None, parse_mode=None):
    """
    Отправляет изображение высокого качества
    """
    # Сохраняем с максимальным качеством
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        # Увеличиваем DPI для лучшего качества
        image.save(tmp.name, 'PNG', dpi=(300, 300), optimize=True, quality=95)

        with open(tmp.name, 'rb') as photo:
            bot.send_photo(
                chat_id,
                photo,
                caption=caption,
                parse_mode=parse_mode
            )

        os.unlink(tmp.name)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"Пользователь {message.from_user.first_name} нажал старт")
    bot.send_message(message.chat.id,
                     constants.WELCOME_TEXT,
                     parse_mode='Markdown')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id,
                     constants.HELP_TEXT,
                     parse_mode='Markdown')


# Обработка регистрации (только в личных сообщениях)
@bot.message_handler(commands=['register'], chat_types=['private'])
def start_registration(message):
    user_id = message.from_user.id
    logger.info(f"Старт регистрации от: {user_id}")

    user_registration_data[user_id] = {'waiting_for_login': True}
    bot.send_message(
        message.chat.id,
        constants.REGISTRATION_MSG,
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda m: (
    m.chat.type == 'private' and
    m.from_user.id in user_registration_data and
    user_registration_data[m.from_user.id].get('waiting_for_login')
))
def handle_registration_input(message):
    user_id = message.from_user.id
    nickname = message.text.strip()
    logger.info(f"Пришли данные для регистрации от {user_id}, "
                f"faceit nickname: {nickname}")
    user_data = register_user(user_id, nickname)

    # Если пользователя не существует
    if user_data is None:
        bot.send_message(
            message.chat.id,
            constants.NICKNAME_NOT_FOUND,
            parse_mode='Markdown'
        )
        return False
    # Если пользователь существует
    user_registration_data[user_id] = {'waiting_for_login': False}
    stat_img = generate_player_card(user_data)

    send_high_quality_photo(message.chat.id,
                            stat_img,
                            constants.REGISTRATION_OK)


@bot.message_handler(commands=['stat'])
def handle_stat_command(message):
    # Разбиваем сообщение на части: команда и параметры
    parts = message.text.split()
    # Если есть параметры после команды (/stat никнейм)
    if len(parts) > 1:
        nickname = parts[1]
        logger.debug(f"Показываем статистику `nickname`: {nickname}")
    else:
        telegram_id = message.from_user.id
        logger.debug(f"Показываем статистику `telegram ID`: {telegram_id}")
        nickname = get_faceit_nickname_from_db(telegram_id)
        # Если пользователя не зарегестрирован
        if nickname is None:
            bot.send_message(
                message.chat.id,
                constants.NOT_REGISTERED,
                parse_mode='Markdown'
            )
            return False

    user_data = get_user_stat(nickname)

    # Если пользователя не существует
    if user_data is None:
        bot.send_message(
            message.chat.id,
            constants.NICKNAME_NOT_FOUND,
            parse_mode='Markdown'
        )
        return False

    stat_img = generate_player_card(user_data)
    send_high_quality_photo(
        message.chat.id,
        stat_img,
        caption=f"{constants.STAT_MSG} <b>{nickname}</b>",
        parse_mode='HTML'
    )


# Запуск бота
if __name__ == "__main__":
    try:
        logger.info("----- Бот запущен -----")
        bot.infinity_polling()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
    finally:
        logger.info("----- Бот остановлен -----")
