import logging
import xml.etree.ElementTree as ET

from handler.constants import (ADDRESS, DOMEN_FTP, FEEDS_FOLDER,
                               NEW_FEEDS_FOLDER, NEW_IMAGE_FOLDER, PROTOCOL)
from handler.decorators import time_of_function
from handler.exceptions import DirectoryCreationError, EmptyFeedsListError
from handler.logging_config import setup_logging
from handler.mixins import FileMixin

setup_logging()


class FeedHandler(FileMixin):
    """
    Класс, предоставляющий интерфейс
    для обработки xml-файлов.
    """

    def __init__(
        self,
        feeds_folder: str = FEEDS_FOLDER,
        new_feeds_folder: str = NEW_FEEDS_FOLDER,
        new_image_folder: str = NEW_IMAGE_FOLDER
    ) -> None:
        self.feeds_folder = feeds_folder
        self.new_feeds_folder = new_feeds_folder
        self.new_image_folder = new_image_folder

    def _save_xml(self, elem, file_folder: str, filename: str) -> None:
        """Защищенный метод, сохраняет отформатированные файлы."""
        root = elem
        self._indent(root)
        formatted_xml = ET.tostring(root, encoding='unicode')
        file_path = self._make_dir(file_folder)
        with open(
            file_path / f'new_{filename}',
            'w',
            encoding='utf-8'
        ) as f:
            f.write(formatted_xml)

    def _get_image_dict(self) -> dict:
        image_dict = {}
        try:
            filenames_list = self._get_filenames_list(self.new_image_folder)
        except (DirectoryCreationError, EmptyFeedsListError):
            logging.warning(
                'Нет подходящих офферов для обрамления изображений'
            )
            return image_dict
        for img_file in filenames_list:
            try:
                offer_id = img_file.split('.')[0]
                if offer_id not in image_dict:
                    image_dict[offer_id] = []
                image_dict[offer_id].append(img_file)
            except (ValueError, IndexError):
                logging.warning(
                    'Не удалось присвоить изображение '
                    f'{img_file} ключу {offer_id}'
                )
                continue
            except Exception as e:
                logging.error(
                    'Неожиданная ошибка во время '
                    f'сборки словаря image_dict: {e}'
                )
                raise
        return image_dict

    @time_of_function
    def image_replacement(self) -> None:
        """Метод, подставляющий в фиды новые изображения."""
        deleted_images = 0
        input_images = 0
        try:
            image_dict = self._get_image_dict()

            if not image_dict:
                logging.warning('Нет подходящих изображений для замены')
                return

            filenames_list = self._get_filenames_list(self.feeds_folder)

            for file_name in filenames_list:
                tree = self._get_tree(file_name, self.feeds_folder)
                root = tree.getroot()

                offers = list(root.findall('.//offer'))
                for offer in offers:
                    offer_id = str(offer.get('id'))

                    if not offer_id:
                        continue

                    if offer_id not in image_dict:
                        continue

                    pictures = offer.findall('picture')
                    for picture in pictures:
                        offer.remove(picture)
                    deleted_images += len(pictures)

                    for img_file in image_dict[offer_id]:
                        picture_tag = ET.SubElement(offer, 'picture')
                        picture_tag.text = (
                            f'{PROTOCOL}://{DOMEN_FTP}/'
                            f'{ADDRESS}/{img_file}'
                        )
                        input_images += 1
                self._save_xml(root, self.new_feeds_folder, file_name)
            logging.info(
                '\nКоличество удаленных изображений в '
                f'оффере - {deleted_images}\n'
                f'Количество добавленных изображений - {input_images}\n'
                'Количество неизмененных '
                f'изображений - {deleted_images - input_images}'
            )

        except Exception as e:
            logging.error(f'Ошибка в image_replacement: {e}')
            raise
