import logging
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

from handler.constants import ENCODING, FEEDS_FOLDER
from handler.decorators import retry_on_network_error, time_of_function
from handler.exceptions import (EmptyFeedsListError, EmptyXMLError,
                                InvalidXMLError)
from handler.feeds import FEEDS
from handler.logging_config import setup_logging
from handler.mixins import FileMixin

setup_logging()


class FeedSave(FileMixin):
    """
    Класс, предоставляющий интерфейс для скачивания,
    валидации и сохранения фида в xml-файл.
    """
    load_dotenv()

    def __init__(
        self,
        feeds_list: tuple[str, ...] = FEEDS,
        feeds_folder: str = FEEDS_FOLDER
    ) -> None:
        if not feeds_list:
            logging.error('Не передан список фидов.')
            raise EmptyFeedsListError('Список фидов пуст.')

        self.feeds_list = feeds_list
        self.feeds_folder = feeds_folder

    @retry_on_network_error(max_attempts=3, delays=(2, 5, 10))
    def _get_file(self, feed: str):
        """Защищенный метод, получает фид по ссылке."""
        try:
            response = requests.get(feed, stream=True, timeout=(10, 60))

            if response.status_code == requests.codes.ok:
                response.content
                return response

        except requests.RequestException as error:
            logging.error('Ошибка при загрузке %s: %s', feed, error)
            return None

    def _get_filename(self, feed: str) -> tuple[str, str]:
        """Защищенный метод, формирующий имя xml-файлу."""
        feedname = feed.split('/')[-1].split('.')[0]
        return f'{feedname}_search.xml', f'{feedname}_network.xml'

    def _validate_xml(self, xml_content: bytes) -> str:
        """
        Валидирует XML.
        Возвращает декодированное содержимое.
        """
        if not xml_content.strip():
            logging.error('Получен пустой XML-файл')
            raise EmptyXMLError('XML пуст')
        try:
            decoded_content = xml_content.decode(ENCODING)
        except UnicodeDecodeError:
            logging.error('Ошибка декодирования XML-файла')
            raise
        try:
            ET.fromstring(decoded_content)
        except ET.ParseError as e:
            logging.error('XML-файл содержит синтаксические ошибки')
            raise InvalidXMLError(f'XML содержит синтаксические ошибки: {e}')
        return decoded_content

    @time_of_function
    def save_xml(self) -> None:
        """Метод, сохраняющий фиды в xml-файлы"""
        total_files: int = len(self.feeds_list)
        saved_copy = 0
        saved_files = 0
        folder_path = self._make_dir(self.feeds_folder)
        for feed in self.feeds_list:
            file_name, file_name_copy = self._get_filename(feed)
            file_path = folder_path / file_name
            response = self._get_file(feed)
            if response is None:
                logging.warning('XML-файл %s не получен.', file_name)
                continue
            try:
                xml_content = response.content
                decoded_content = self._validate_xml(xml_content)
                xml_tree = ET.fromstring(decoded_content)
                self._indent(xml_tree)
                tree = ET.ElementTree(xml_tree)
                with open(file_path, 'wb') as file:
                    tree.write(file, encoding=ENCODING, xml_declaration=True)

                backup_path = folder_path / file_name_copy
                with open(backup_path, 'wb') as file:
                    tree.write(file, encoding=ENCODING, xml_declaration=True)

                saved_files += 1
                saved_copy += 1
                logging.info(
                    '\nФайл %s успешно сохранен'
                    '\nКопия %s успешно сохранена',
                    file_name,
                    file_name_copy
                )
            except (EmptyXMLError, InvalidXMLError) as error:
                logging.error('Ошибка валидации XML %s: %s', file_name, error)
                continue
            except Exception as error:
                logging.error(
                    'Ошибка обработки файла %s: %s',
                    file_name,
                    error
                )
                continue
        logging.info(
            '\nУспешно записано %s файлов из %s.'
            '\nСоздано копий - %s из %s.',
            saved_files,
            total_files,
            saved_copy,
            total_files
        )
