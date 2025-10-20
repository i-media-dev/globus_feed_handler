import logging
import xml.etree.ElementTree as ET

from handler.constants import (ADDRESS, DOMEN_FTP, FEEDS_FOLDER, FEEDS_POSTFIX,
                               NEW_FEEDS_FOLDER, NEW_IMAGE_FOLDER, PROMO_TEXT,
                               PROTOCOL)
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
            filenames = self._get_filenames_set(self.new_image_folder)
        except (DirectoryCreationError, EmptyFeedsListError):
            logging.warning(
                'Нет подходящих офферов для обрамления изображений'
            )
            return image_dict
        for img_file in filenames:
            try:
                offer_id = img_file.split('.')[0]
                if offer_id not in image_dict:
                    image_dict[offer_id] = []
                image_dict[offer_id].append(img_file)
            except (ValueError, IndexError):
                logging.warning(
                    'Не удалось присвоить изображение %s ключу %s',
                    img_file,
                    offer_id
                )
                continue
            except Exception as error:
                logging.error(
                    'Неожиданная ошибка во время '
                    'сборки словаря image_dict: %s',
                    error
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

            filenames = self._get_filenames_set(self.feeds_folder)

            for filename in filenames:
                tree = self._get_tree(filename, self.feeds_folder)
                root = tree.getroot()
                postfix = FEEDS_POSTFIX[filename.split('_')[-1]]
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

                    for img_file in image_dict[image_key]:
                        picture_tag = ET.SubElement(offer, 'picture')
                        picture_tag.text = (
                            f'{PROTOCOL}://{DOMEN_FTP}/'
                            f'{ADDRESS}/{img_file}'
                        )
                        input_images += 1
                self._save_xml(root, self.new_feeds_folder, filename)
            images_not_change = deleted_images - input_images
            logging.info(
                '\nКоличество удаленных изображений в оффере - %s'
                '\nКоличество добавленных изображений - %s'
                '\nКоличество неизмененных изображений - %s',
                deleted_images,
                input_images,
                images_not_change
            )

        except Exception as error:
            logging.error('Ошибка в image_replacement: %s', error)
            raise

    def add_sales_notes(self):
        allowed_offers = set()
        added_promo_text = 0
        try:
            image_names = self._get_filenames_set(self.new_image_folder)
            offers_promocodes_dict = {
                f'{filename.split('_')[0]}_{filename.split('_')[2]}':
                filename.split('_')[1]
                for filename in image_names
            }
            filenames = self._get_filenames_set(self.feeds_folder)

            for image_name in image_names:
                offer_id_target = image_name.split('_')[0]
                allowed_offers.add(offer_id_target)

            for filename in filenames:
                tree = self._get_tree(filename, self.feeds_folder)
                root = tree.getroot()
                offers = list(root.findall('.//offer'))
                postfix = FEEDS_POSTFIX[filename.split('_')[-1]]

                for offer in offers:
                    offer_id = str(offer.get('id'))

                    if offer_id not in allowed_offers:
                        continue

                    offer_key = f'{offer_id}_{postfix}'

                    sales_notes_tag = ET.SubElement(offer, 'sales_notes')
                    sales_notes_tag.text = PROMO_TEXT.format(
                        '10',
                        offers_promocodes_dict[offer_key],
                        'Москве и области',
                        '6000'
                    )
                    added_promo_text += 1
            logging.info(
                'Тег sales_notes добавлен в %s офферов',
                added_promo_text
            )
        except Exception as error:
            logging.error('Неожиданная ошибка: %s', error)
