import logging

from handler.decorators import time_of_script
from handler.feeds_handler import FeedHandler
from handler.feeds_save import FeedSave
from handler.image_handler import FeedImage
from handler.logging_config import setup_logging

setup_logging()


@time_of_script
def main():
    try:
        save_client = FeedSave()
        image_client = FeedImage()
        handler_client = FeedHandler()

        save_client.save_xml()
        image_client.get_images()
        image_client.add_frame()
        handler_client.image_replacement()
    except Exception as e:
        logging.error(f'Неожиданная ошибка: {e}')
        raise


if __name__ == '__main__':
    main()
