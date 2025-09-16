import os
import tempfile
from io import BytesIO

import cairosvg
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


class ImageLoadError(Exception):
    """Кастомное исключение для ошибок загрузки изображений"""
    pass


def load_image_safe(url, default_size):
    """
    Безопасная загрузка изображения с поддержкой SVG

    Args:
        url: URL изображения
        default_size: размер (width, height)

    Returns:
        Image object

    Raises:
        ImageLoadError: если не удалось загрузить изображение
    """

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()

        if 'svg' in content_type or url.endswith('.svg'):
            # Это SVG - конвертируем в PNG
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    cairosvg.svg2png(bytestring=response.content,
                                     write_to=tmp.name,
                                     output_width=default_size[0],
                                     output_height=default_size[1])

                    img = Image.open(tmp.name)
                    os.unlink(tmp.name)

                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    return img

            except Exception as e:
                raise ImageLoadError(f"Ошибка конвертации SVG {url}: {e}")

        else:
            # Это обычное изображение
            try:
                img = Image.open(BytesIO(response.content))
                img = img.resize(default_size)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                return img
            except Exception as e:
                raise ImageLoadError(
                    f"Ошибка обработки изображения {url}: {e}"
                )

    except requests.RequestException as e:
        raise ImageLoadError(f"Ошибка HTTP запроса к {url}: {e}")
    except Exception as e:
        raise ImageLoadError(f"Неизвестная ошибка при загрузке {url}: {e}")


def create_placeholder(size, color):
    """Создает placeholder изображение"""
    return Image.new('RGBA', size, color)


def draw_stat_table(draw, x, y, stat_data, table_width, table_height,
                    title_font, stat_title_font, stat_value_font):
    """
    Отрисовка одной таблицы статистики

    Args:
        draw: ImageDraw объект
        x, y: координаты левого верхнего угла
        stat_data: данные статистики
        table_width, table_height: размеры таблицы
        title_font, stat_title_font, stat_value_font: шрифты
    """
    # Рисуем фон таблицы
    draw.rectangle([x, y, x + table_width, y + table_height],
                   fill=(45, 45, 45), outline=(80, 80, 80), width=2)

    # Заголовок таблицы
    title_bbox = draw.textbbox((0, 0), stat_data['title'], font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text((x + (table_width - title_width) // 2, y + 15),
              stat_data['title'], fill=(255, 255, 255), font=title_font)

    # Основное значение заголовка
    is_low_kdr_or_rating = (
        stat_data['title'] in ['Avg. KDR', 'FA Rating'] and
        float(stat_data['main_value']) < 1
    )
    is_low_winrate = (
        stat_data['title'] == 'Winrate' and
        float(stat_data['main_value']) < 50
    )

    if is_low_kdr_or_rating or is_low_winrate:
        fill_color = (230, 118, 118)
    else:
        fill_color = (214, 243, 148)

    main_value_bbox = draw.textbbox((0, 0), stat_data['main_value'],
                                    font=stat_title_font)
    main_value_width = main_value_bbox[2] - main_value_bbox[0]
    draw.text((x + (table_width - main_value_width) // 2, y + 50),
              stat_data['main_value'], fill=fill_color,
              font=stat_title_font)

    # Разделительная линия
    draw.line([x + 20, y + 85, x + table_width - 20, y + 85],
              fill=(100, 100, 100), width=1)

    # Статистические данные
    for i, item in enumerate(stat_data['items']):
        item_y = y + 95 + i * 25
        draw.text((x + 20, item_y), item['title'],
                  fill=(200, 200, 200), font=stat_value_font)
        draw.text((x + table_width - 20, item_y), item['value'],
                  fill=(255, 255, 255), font=stat_value_font, anchor="ra")


def generate_player_card(data):
    """
    Генерация карточки игрока

    Returns:
        Image object

    Raises:
        Exception: если произошла критическая ошибка
    """
    # Создаем изображение с темно-серым фоном
    width, height = 1600, 820  # Увеличиваем высоту для таблиц
    image = Image.new('RGB', (width, height), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)

    try:
        # Загружаем шрифты
        montserrat_medium = "Montserrat-Font/Montserrat-Medium.ttf"
        montserrat_bold = "Montserrat-Font/Montserrat-Bold.ttf"

        name_font = ImageFont.truetype(montserrat_bold, 40)
        elo_font = ImageFont.truetype(montserrat_medium, 36)
        title_font = ImageFont.truetype(montserrat_bold, 28)
        stat_title_font = ImageFont.truetype(montserrat_bold, 24)
        stat_value_font = ImageFont.truetype(montserrat_medium, 22)
        section_font = ImageFont.truetype(montserrat_bold, 32)

        # Загружаем аватарку с обработкой ошибок
        try:
            avatar_img = load_image_safe(data['avatar_url'], (150, 150))
            mask = Image.new('L', (150, 150), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 150, 150), fill=255)
            avatar_img.putalpha(mask)
            image.paste(avatar_img, (50, 50), avatar_img)
        except ImageLoadError:
            placeholder = create_placeholder((150, 150), (100, 100, 100, 255))
            image.paste(placeholder, (50, 50), placeholder)

        # Загружаем флаг с обработкой ошибок
        try:
            flag_img = load_image_safe(data['flag_url'], (60, 45))
            image.paste(flag_img, (220, 55), flag_img)
        except ImageLoadError:
            placeholder = create_placeholder((60, 45), (200, 100, 100, 255))
            image.paste(placeholder, (220, 55), placeholder)

        # Загружаем уровень с обработкой ошибок
        try:
            level_img = load_image_safe(data['level_url'], (70, 70))
            image.paste(level_img, (220, 110), level_img)
        except ImageLoadError:
            placeholder = create_placeholder((45, 45), (100, 200, 100, 255))
            image.paste(placeholder, (220, 110), placeholder)

        # Имя игрока
        draw.text((295, 55), data['name'],
                  fill=(255, 255, 255), font=name_font)

        # Уровень и ELO
        draw.text((295, 120), data['elo'],
                  fill=(255, 255, 255), font=elo_font)

        # Параметры таблиц
        table_width = 350
        table_height = 180
        table_margin = 30
        start_y = 300  # Начальная позиция Y для таблиц
        section_margin = 40  # Отступ между секциями
        title_table_margin = 5  # Отступ между заголовком секции и таблицами

        # Разделительная линия под аватаркой с ником и эло
        draw.line([40, 230, width - 40, 230],
                  fill=(100, 100, 100), width=1)

        # Первая секция: Статистика за всё время
        section1_title_y = start_y - 40
        draw.text((50, section1_title_y), "Статистика за всё время",
                  fill=(255, 255, 255), font=section_font)

        # Таблицы первой секции (с увеличенным отступом от заголовка)
        table_start_y = section1_title_y + 50 + title_table_margin
        for i, stat_data in enumerate(data['view1_stats']):
            x = 50 + i * (table_width + table_margin)
            draw_stat_table(draw, x, table_start_y, stat_data, table_width,
                            table_height,
                            title_font, stat_title_font, stat_value_font)

        # Вторая секция: Статистика за последние 50 матчей
        section2_title_y = table_start_y + table_height + section_margin
        draw.text((50, section2_title_y), "Статистика за последние 50 матчей",
                  fill=(255, 255, 255), font=section_font)

        # Таблицы второй секции (с увеличенным отступом от заголовка)
        table_start_y2 = section2_title_y + 50 + title_table_margin
        for i, stat_data in enumerate(data['view2_stats']):
            x = 50 + i * (table_width + table_margin)
            draw_stat_table(draw, x, table_start_y2, stat_data, table_width,
                            table_height,
                            title_font, stat_title_font, stat_value_font)
        return image

    except Exception as e:
        # Пробрасываем ошибку
        raise Exception(f"Ошибка при генерации карточки: {e}")


def download_page(url):
    try:
        # Отправляем GET запрос
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise (f"Ошибка при загрузке страницы {url}: {e}")


def parse_view_stats_div(div):
    # Находим все блоки с классом stats_totals_block_wrapper
    stats_blocks = div.find_all(
        'div',
        class_='stats_totals_block_wrapper')

    all_data = []

    # Проходим по каждому блоку
    for block in stats_blocks:

        block_data = {}

        # Заголовок блока
        title_span = block.find(
            'span',
            class_='stats_totals_block_title_text')
        if title_span:
            block_data['title'] = title_span.get_text(strip=True)

        # Основное значение
        main_value_span = block.find(
            'span',
            class_='stats_totals_block_main_value_span')
        if main_value_span:
            block_data['main_value'] = main_value_span.get_text(strip=True)

        # Все дополнительные значения
        item_values = []
        item_titles = block.find_all('span',
                                     class_='stats_totals_block_item_title')
        item_spans = block.find_all('span',
                                    class_='stats_totals_block_item_value')

        for title_span, value_span in zip(item_titles, item_spans):
            item_data = {
                'title': title_span.get_text(strip=True),
                'value': value_span.get_text(strip=True)
            }
            item_values.append(item_data)

        block_data['items'] = item_values
        all_data.append(block_data)

    return all_data


def parse_faceitanalyser(html_content):
    data = {}
    soup = BeautifulSoup(html_content, 'html.parser')

    # Ищем изображение аватарки
    avatar_img = soup.find('img', class_='stats_profile_avatar')
    if avatar_img and avatar_img.get('src'):
        data['avatar_url'] = avatar_img['src']

    # Ищем изображения флага и уровня игрока
    level_images = soup.find_all('img', class_='stats_profile_level_image')

    for i, level_img in enumerate(level_images[:2]):  # Берем первые два
        if level_img and level_img.get('src'):
            image_url = level_img['src']
            if i == 0:  # первый идёт флаг
                data['flag_url'] = "https://faceitanalyser.com/" + image_url
            else:  # второй идёт картинка с уровнем 1-10
                data['level_url'] = "https://faceitanalyser.com/" + image_url

    # Ищем классы elo и name
    for class_ in ['stats_profile_name_span', 'stats_profile_elo_span']:
        span = soup.find('span', class_=class_)
        if span:
            span_text = span.get_text(strip=True)
            data[class_.split('_')[2]] = span_text
        else:
            # Элемент не найден
            return None

    # Находим интересующие div
    for div_id in ['view1_stats', 'view2_stats']:
        div = soup.find('div', id=div_id)
        if not div:
            return None
        data[div_id] = parse_view_stats_div(div)

    return data
