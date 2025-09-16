import sqlite3
import os


def init_database():
    # Получаем текущую рабочую директорию
    current_dir = os.getcwd()
    print(f"📁 Текущая директория: {current_dir}")

    # Путь к файлу базы данных
    db_path = 'faceit_bot.sqlite3'
    full_path = os.path.join(current_dir, db_path)
    print(f"📋 Полный путь к БД: {full_path}")

    # Удаляем существующую базу данных (если есть)
    if os.path.exists(full_path):
        os.remove(full_path)
        print("🗑️ Существующая база данных удалена")
    else:
        print("ℹ️ Файл базы данных не найден, создаем новый")

    # Создаем новую базу данных и подключаемся к ней
    try:
        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()

        # Создаем таблицу users
        cursor.execute('''
        CREATE TABLE users (
            telegram_id INTEGER PRIMARY KEY,
            faceit_nickname TEXT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Создаем индексы
        cursor.execute('CREATE INDEX idx_telegram_id ON users (telegram_id)')
        cursor.execute('CREATE INDEX idx_faceit_nickname ON users (faceit_nickname)')

        # Сохраняем изменения и закрываем соединение
        conn.commit()
        conn.close()

        print("✅ База данных создана успешно!")

        # Проверяем, что файл действительно создался
        if os.path.exists(full_path):
            file_size = os.path.getsize(full_path)
            print(f"📊 Файл БД создан, размер: {file_size} байт")
        else:
            print("❌ Файл БД не создан!")

    except Exception as e:
        print(f"❌ Ошибка при создании БД: {e}")


if __name__ == "__main__":
    init_database()