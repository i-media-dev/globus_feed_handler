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

        except requests.RequestException as e:
            logging.error(f'Ошибка при загрузке {feed}: {e}')
            return None

    def _get_filename(self, feed: str) -> str:
        """Защищенный метод, формирующий имя xml-файлу."""
        return feed.split('/')[-1]

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
        saved_files = 0
        folder_path = self._make_dir(self.feeds_folder)
        for feed in self.feeds_list:
            file_name = self._get_filename(feed)
            file_path = folder_path / file_name
            response = self._get_file(feed)
            if response is None:
                logging.warning(f'XML-файл {file_name} не получен.')
                continue
            try:
                xml_content = response.content
                decoded_content = self._validate_xml(xml_content)
                xml_tree = ET.fromstring(decoded_content)
                self._indent(xml_tree)
                tree = ET.ElementTree(xml_tree)
                with open(file_path, 'wb') as file:
                    tree.write(file, encoding=ENCODING, xml_declaration=True)
                saved_files += 1
                logging.info(f'Файл {file_name} успешно сохранен')
            except (EmptyXMLError, InvalidXMLError) as e:
                logging.error(f'Ошибка валидации XML {file_name}: {e}')
                continue
            except Exception as e:
                logging.error(f'Ошибка обработки файла {file_name}: {e}')
                continue
        logging.info(
            f'Успешно записано {saved_files} файлов из {total_files}.'
        )
