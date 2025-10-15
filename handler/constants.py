import os

from dotenv import load_dotenv

load_dotenv()

PROTOCOL = 'https'
"""Протокол запроса."""

ADDRESS = 'projects/globus/new_images'
"""Путь к файлу."""

DOMEN_FTP = 'feeds.i-media.ru'
"""Домен FTP-сервера."""

RGB_COLOR_SETTINGS = (255, 255, 255)
"""Цвет RGB холста."""

RGBA_COLOR_SETTINGS = (0, 0, 0, 0)
"""Цвет RGBA холста."""

NUMBER_PIXELS_CANVAS = 40
"""Количество пикселей для подгонки холста."""

NUMBER_PIXELS_IMAGE = 200
"""Количество пикселей для подгонки изображения."""

NAME_OF_SHOP = 'globus'
"""Константа названия магазина."""

FRAMES = {
    'promocode1': 'RST1.png',
    'promocode2': 'RST2.png',
    'promocode3': 'RST3.png',
    'promocode4': 'RST4.png',
    'promocode5': 'RST5.png',
    'promocode6': 'RST6.png'
}
"""Название рамок, в зависимости от промокода."""

FRAME_FOLDER = os.getenv('FRAME_FOLDER', 'frame')
"""Константа стокового названия директории c рамкой"""

FEEDS_FOLDER = os.getenv('FEEDS_FOLDER', 'temp_feeds')
"""Константа стокового названия директории с фидами."""

NEW_FEEDS_FOLDER = os.getenv('NEW_FEEDS_FOLDER', 'new_feeds')
"""Константа стокового названия директории с измененными фидами."""

IMAGE_FOLDER = os.getenv('IMAGE_FOLDER', 'old_images')
"""Константа стокового названия директории с изображениями."""

NEW_IMAGE_FOLDER = os.getenv('NEW_IMAGE_FOLDER', 'new_images')
"""Константа стокового названия директории измененных изображений."""

ENCODING = 'utf-8'
"""Кодировка по умолчанию."""
