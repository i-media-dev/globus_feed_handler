import logging
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from handler.constants import (DEFAULT_IMAGE_SIZE, FEEDS_FOLDER, FRAME_FOLDER,
                               FRAMES_NET, FRAMES_SRCH, IMAGE_FOLDER,
                               NEW_IMAGE_FOLDER, NUMBER_PIXELS_IMAGE,
                               RGB_COLOR_SETTINGS)
from handler.decorators import time_of_function
from handler.exceptions import DirectoryCreationError, EmptyFeedsListError
from handler.feeds import FEEDS
from handler.logging_config import setup_logging
from handler.mixins import FileMixin

setup_logging()


class FeedImage(FileMixin):
    """
    Класс, предоставляющий интерфейс
    для работы с изображениями.
    """

    def __init__(
        self,
        feeds_folder: str = FEEDS_FOLDER,
        frame_folder: str = FRAME_FOLDER,
        image_folder: str = IMAGE_FOLDER,
        new_image_folder: str = NEW_IMAGE_FOLDER,
        feeds_list: tuple[str, ...] = FEEDS,
        number_pixels_image: int = NUMBER_PIXELS_IMAGE
    ) -> None:
        self.frame_folder = frame_folder
        self.feeds_folder = feeds_folder
        self.image_folder = image_folder
        self.new_image_folder = new_image_folder
        self.feeds_list = feeds_list
        self.number_pixels_image = number_pixels_image
        self._existing_image_offers = set()
        self._existing_framed_offers = set()

    def _get_image_data(self, url: str) -> tuple:
        """
        Защищенный метод, загружает данные изображения
        и возвращает (image_data, image_format).
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image_format = image.format.lower() if image.format else None
            return response.content, image_format
        except Exception as error:
            logging.error('Ошибка при загрузке изображения %s: %s', url, error)
            return None, None

    def _get_image_filename(
        self,
        offer_id: str,
        image_data: bytes,
        image_format: str
    ) -> str:
        """Защищенный метод, создает имя файла с изображением."""
        if not image_data or not image_format:
            return ''
        return f'{offer_id}.{image_format}'

    def _build_offers_set(self, folder: str, target_set: set) -> None:
        """Защищенный метод, строит множество всех существующих офферов."""
        try:
            for file_name in self._get_filenames_list(folder):
                offer_image = file_name.split('.')[0]
                if offer_image:
                    target_set.add(offer_image)

            logging.info(
                'Построен кэш для %s файлов',
                {len(target_set)}
            )
        except EmptyFeedsListError:
            raise
        except DirectoryCreationError:
            raise
        except Exception as error:
            logging.error(
                'Неожиданная ошибка при сборе множества '
                'скачанных изображений: %s',
                error
            )
            raise

    def _get_category_dict(self, filenames_list: list) -> dict[str, str]:
        categories_dict = {}
        try:
            for filename in filenames_list:
                tree = self._get_tree(filename, self.feeds_folder)
                root = tree.getroot()
                categories = root.findall('.//category')

                for category in categories:
                    category_id = category.get('id')
                    category_parentid = category.get('parentId')

                    if category_parentid not in FRAMES_NET:
                        continue

                    categories_dict[category_id] = category_parentid
            return categories_dict
        except Exception as error:
            logging.error('Неожиданная ошибка: %s', error)
            raise

    def _save_image(
        self,
        image_data: bytes,
        folder_path: Path,
        image_filename: str
    ) -> None:
        """Защищенный метод, сохраняет изображение по указанному пути."""
        try:
            with Image.open(BytesIO(image_data)) as img:
                file_path = folder_path / image_filename
                img.load()
                img.save(file_path)
        except Exception as error:
            logging.error(
                'Ошибка при сохранении %s: %s',
                image_filename,
                error
            )

    @time_of_function
    def get_images(self) -> None:
        """Метод получения и сохранения изображений из xml-файла."""
        total_offers_processed = 0
        offers_with_images = 0
        images_downloaded = 0
        offers_skipped_existing = 0

        try:
            self._build_offers_set(
                self.image_folder,
                self._existing_image_offers
            )
        except (DirectoryCreationError, EmptyFeedsListError):
            logging.warning(
                'Директория с изображениями отсутствует. Первый запуск'
            )
        try:
            filenames_list = self._get_filenames_list(self.feeds_folder)
            for file_name in filenames_list:
                tree = self._get_tree(file_name, self.feeds_folder)
                root = tree.getroot()
                offers = root.findall('.//offer')
                for offer in offers:
                    offer_id = offer.get('id')
                    total_offers_processed += 1

                    picture = offer.find('picture')
                    if picture is None:
                        continue

                    offer_image = picture.text
                    if not offer_image:
                        continue

                    offers_with_images += 1

                    if str(offer_id) in self._existing_image_offers:
                        offers_skipped_existing += 1
                        continue

                    image_data, image_format = self._get_image_data(
                        offer_image
                    )
                    image_filename = self._get_image_filename(
                        str(offer_id),
                        image_data,
                        image_format
                    )
                    folder_path = self._make_dir(self.image_folder)
                    self._save_image(
                        image_data,
                        folder_path,
                        image_filename
                    )
                    images_downloaded += 1
            logging.info(
                '\nВсего обработано фидов - %s'
                '\nВсего обработано офферов - %s'
                '\nВсего офферов с подходящими изображениями - %s'
                '\nВсего изображений скачано %s'
                '\nПропущено офферов с уже скачанными изображениями - %s',
                len(filenames_list),
                total_offers_processed,
                offers_with_images,
                images_downloaded,
                offers_skipped_existing
            )
        except Exception as error:
            logging.error(
                'Неожиданная ошибка при получении изображений: %s',
                error
            )

    @time_of_function
    def add_frame(self) -> None:
        """Метод форматирует изображения и добавляет рамку."""
        total_framed_images = 0
        total_failed_images = 0
        skipped_images = 0
        skipped_unsuitable_offers = 0
        file_path = self._make_dir(self.image_folder)
        frame_path = self._make_dir(self.frame_folder)
        new_file_path = self._make_dir(self.new_image_folder)
        images_names_list = self._get_filenames_list(self.image_folder)

        try:
            self._build_offers_set(
                self.new_image_folder,
                self._existing_framed_offers
            )
        except (DirectoryCreationError, EmptyFeedsListError):
            logging.warning(
                'Директория с форматированными изображениями отсутствует. '
                'Первый запуск'
            )
        images_dict = {}
        for image_name in images_names_list:
            offer_id = image_name.split('.')[0]
            images_dict[offer_id] = image_name

        try:
            filenames_list = self._get_filenames_list(self.feeds_folder)
            categories_dict = self._get_category_dict(filenames_list)

            for file_name in filenames_list:
                frame_name_dict = FRAMES_NET
                postfix = 'net'

                if 'search' in file_name.split('_')[-1]:
                    frame_name_dict = FRAMES_SRCH
                    postfix = 'srch'

                tree = self._get_tree(file_name, self.feeds_folder)
                root = tree.getroot()
                offers = root.findall('.//offer')

                for offer in offers:
                    offer_id = str(offer.get('id'))
                    category_elem = offer.find('categoryId')

                    if offer_id in self._existing_framed_offers:
                        skipped_images += 1
                        continue

                    if category_elem is None or \
                            category_elem.text not in categories_dict:
                        skipped_unsuitable_offers += 1
                        continue

                    category_id = category_elem.text

                    if offer_id not in images_dict:
                        skipped_unsuitable_offers += 1
                        continue

                    try:
                        parent_id = categories_dict[category_id]
                        image_name = images_dict[offer_id]
                        name_of_frame = frame_name_dict[parent_id]

                        with Image.open(file_path / image_name) as image:
                            image.load()
                            image_width, image_height = image.size

                        with Image.open(frame_path / name_of_frame) as frame:
                            frame_resized = frame.resize(DEFAULT_IMAGE_SIZE)

                        final_image = Image.new(
                            'RGB',
                            DEFAULT_IMAGE_SIZE,
                            RGB_COLOR_SETTINGS
                        )

                        canvas_width, canvas_height = DEFAULT_IMAGE_SIZE
                        x_position = (canvas_width - image_width) // 2
                        y_position = (
                            canvas_height - image_height
                        ) // 2

                        if image_width > canvas_width \
                                or image_height > canvas_height:
                            new_width = int(image_width * 50 / 100)
                            new_height = int(image_height * 50 / 100)
                            image = image.resize((new_width, new_height))
                            x_position = (canvas_width - new_width) // 2
                            y_position = (
                                canvas_height - new_height
                            ) // 2

                        final_image.paste(image, (x_position, y_position))
                        final_image.paste(frame_resized, (0, 0), frame_resized)
                        filename = f'{offer_id}_{postfix}.png'
                        final_image.save(new_file_path / filename, 'PNG')
                        total_framed_images += 1

                    except Exception as error:
                        total_failed_images += 1
                        logging.error(
                            'Ошибка при обрамлении %s: %s',
                            offer_id,
                            error
                        )

            logging.info(
                '\nПропущенных офферов с неподходящей категорией - %s'
                '\nКоличество уже обрамленных изображений - %s'
                '\nУспешно обрамлено: %s'
                '\nКоличество изображений обрамленных неудачно - %s',
                skipped_unsuitable_offers,
                skipped_images,
                total_framed_images,
                total_failed_images
            )
        except Exception as error:
            logging.error('Неожиданная ошибка наложения рамки: %s', error)
            raise
