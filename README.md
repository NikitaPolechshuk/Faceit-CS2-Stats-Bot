# Faceit-CS2-Stats-Bot

Бот для анализа статистики с Faceit.сom

Парсит https://faceitanalyser.com/, генерирует картинку с статистикой и отправяет пользователю

Пример:
![Иллюстрация к проекту](https://github.com/NikitaPolechshuk/Faceit-CS2-Stats-Bot/blob/main/example_stat_img.jpeg)

## 🚀 Запуск Бота

Клонируйте репозиторий
```
git clone https://github.com/NikitaPolechshuk/Faceit-CS2-Stats-Bot.git
```

Разверните виртуальное окружение и установите зависимости:
```
cd Faceit-CS2-Stats-Bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Создайте файл .env
```
TELEGRAM_BOT_TOKEN="токен_вашего_бота"
DB_PATH=faceit_bot.sqlite3
```

Инициализация Базы Данных
```
python3 init_db.py
```

Запуск:
```
python3 faceitcs2stats_bot.py
```
