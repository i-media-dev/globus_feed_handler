import logging
import xml.etree.ElementTree as ET

from handler.constants import (ADDRESS, DEFAULT_TEXT, DOMEN_FTP, FEEDS_FOLDER,
                               FEEDS_POSTFIX, NEW_FEEDS_FOLDER,
                               NEW_IMAGE_FOLDER, PROMO_TEXT, PROTOCOL)
from handler.decorators import time_of_function
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

    def _save_xml(
        self,
        elem,
        file_folder: str,
        filename: str,
        prefix='new_'
    ) -> None:
        """Защищенный метод, сохраняет отформатированные файлы."""
        root = elem
        self._indent(root)
        formatted_xml = ET.tostring(root, encoding='unicode')
        file_path = self._make_dir(file_folder)
        with open(
            file_path / f'{prefix}{filename}',
            'w',
            encoding='utf-8'
        ) as f:
            f.write(formatted_xml)

    @time_of_function
    def image_replacement(self) -> None:
        """Метод, подставляющий в фиды новые изображения."""
        deleted_images = 0
        input_images = 0
        try:
            image_dict = self._get_image_dict(self.new_image_folder)

            if not image_dict:
                logging.warning('Нет подходящих изображений для замены')
                return

            filenames = self._get_filenames_set(self.feeds_folder)

            for filename in filenames:
                tree = self._get_tree(filename, self.feeds_folder)
                root = tree.getroot()
                postfix = FEEDS_POSTFIX[filename.split('_')[-1].split('.')[0]]
                offers = list(root.findall('.//offer'))
                for offer in offers:
                    offer_id = str(offer.get('id'))
                    image_key = f'{offer_id}_{postfix}'

                    if not offer_id:
                        continue

                    if image_key not in image_dict:
                        continue

                    pictures = offer.findall('picture')
                    for picture in pictures:
                        offer.remove(picture)
                    deleted_images += len(pictures)

                    picture_tag = ET.SubElement(offer, 'picture')
                    picture_tag.text = (
                        f'{PROTOCOL}://{DOMEN_FTP}/'
                        f'{ADDRESS}/{image_dict[image_key]}'
                    )
                    input_images += 1
                self._save_xml(root, self.new_feeds_folder, filename)
            sum_offers = len(offers) * len(filenames)
            logging.info(
                '\nВсего офферов - %s суммарно в %s фидах'
                '\nКоличество удаленных изображений - %s'
                '\nКоличество добавленных изображений - %s',
                sum_offers,
                len(filenames),
                deleted_images,
                input_images,
            )

        except Exception as error:
            logging.error('Ошибка в image_replacement: %s', error)
            raise

    def add_sales_notes(self):
        added_promo_text = 0
        added_default_text = 0
        try:
            image_dict = self._get_image_dict(self.new_image_folder)
            filenames = self._get_filenames_set(self.new_feeds_folder)

            for filename in filenames:
                tree = self._get_tree(filename, self.new_feeds_folder)
                root = tree.getroot()
                offers = list(root.findall('.//offer'))
                postfix = FEEDS_POSTFIX[filename.split('_')[-1].split('.')[0]]

                for offer in offers:
                    offer_id = str(offer.get('id'))
                    offer_key = f'{offer_id}_{postfix}'

                    try:
                        sales_notes_tag = ET.SubElement(offer, 'sales_notes')
                        if offer_key in image_dict:
                            sales_notes_tag.text = PROMO_TEXT.format(
                                image_dict[offer_key].split(
                                    '.'
                                )[0].split('_')[1]
                            )
                            added_promo_text += 1
                        else:
                            sales_notes_tag.text = DEFAULT_TEXT
                            added_default_text += 1
                    except (IndexError, KeyError) as error:
                        logging.warning(
                            'Не удалось добавить sales_notes '
                            'для оффера %s: %s',
                            offer_id, error
                        )
                self._save_xml(root, self.new_feeds_folder, filename, '')
            sum_offers = len(offers) * len(filenames)
            logging.info(
                '\nВсего офферов - %s суммарно в %s фидах'
                '\nТег sales_notes с дефолтным текстом добавлен в %s офферов'
                '\nТег sales_notes c промокодом добавлен в %s офферов',
                sum_offers,
                len(filenames),
                added_default_text,
                added_promo_text
            )
        except Exception as error:
            logging.error('Неожиданная ошибка: %s', error)
