import logging
import os
from constants import LOG_FILE
from PIL import ImageFile


def get_logger(name):
    # Настройка расширенного логирования
    # Определяем абсолютный путь к лог-файлу
    script_dir = os.path.dirname(os.path.abspath(__file__))
    _log_file = os.path.join(script_dir, LOG_FILE)

    # Отключаем debug логи от Pillow
    logging.getLogger('PIL').setLevel(logging.WARNING)
    ImageFile.LOAD_TRUNCATED_IMAGES = True

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(_log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return logging.getLogger(name)
