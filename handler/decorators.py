import functools
import json
import logging
import time
from datetime import datetime as dt
from http.client import IncompleteRead

import requests

from handler.constants import ATTEMPTION_LOAD_FEED, DATE_FORMAT, TIME_FORMAT
from handler.logging_config import setup_logging

setup_logging()


def time_of_script(func):
    """Универсальный декоратор для логирования выполнения."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_ts = time.time()
        date_str = dt.now().strftime(DATE_FORMAT)

        print(
            f'Функция {func.__name__} начала работу '
            f'{date_str} в {dt.now().strftime(TIME_FORMAT)}'
        )

        status = 'SUCCESS'
        error_type = error_message = None

        try:
            return func(*args, **kwargs)

        except Exception as error:
            status = 'ERROR'
            error_type = type(error).__name__
            error_message = str(error)
            raise

        finally:
            exec_time_sec = round(time.time() - start_ts, 3)

            print(
                f'Функция {func.__name__} завершила работу '
                f'в {dt.now().strftime(TIME_FORMAT)}. '
                f'Время выполнения — {round(exec_time_sec / 60, 2)} мин.'
            )

            log_record = {
                "DATE": date_str,
                "STATUS": status,
                "FUNCTION_NAME": func.__name__,
                "EXECUTION_TIME": exec_time_sec,
                "ERROR_TYPE": error_type,
                "ERROR_MESSAGE": error_message,
                "ENDLOGGING": 1
            }

            logging.info(json.dumps(log_record, ensure_ascii=False))

    return wrapper


def time_of_function(func):
    """
    Декоратор для измерения времени выполнения функции.

    Замеряет время выполнения декорируемой функции и логирует результат
    в секундах и минутах. Время округляется до 3 знаков после запятой
    для секунд и до 2 знаков для минут.

    Args:
        func (callable): Декорируемая функция, время выполнения которой
        нужно измерить.

    Returns:
        callable: Обёрнутая функция с добавленной функциональностью
        замера времени.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logging.info('Функция %s начала работу', func.__name__)
        result = func(*args, **kwargs)
        execution_time = round(time.time() - start_time, 3)
        logging.info(
            'Функция %s завершила работу. '
            'Время выполнения - %s сек. или %s мин.',
            func.__name__,
            execution_time,
            round(execution_time / 60, 2)
        )
        return result
    return wrapper


def retry_on_network_error(
    max_attempts=ATTEMPTION_LOAD_FEED,
    delays=(5, 15, 30)
):
    """Декоратор для повторных попыток скачивания при сетевых ошибках."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None

            while attempt < max_attempts:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except (
                    IncompleteRead,
                    ConnectionResetError,
                    ConnectionError,
                    ConnectionAbortedError,
                    ConnectionRefusedError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ReadTimeout
                ) as error:
                    last_exception = error
                    if attempt < max_attempts:
                        delay = delays[attempt - 1] if attempt - \
                            1 < len(delays) else delays[-1]
                        logging.warning(
                            'Попытка %s/%s неудачна, повтор через %s сек: %s',
                            attempt,
                            max_attempts,
                            delay,
                            error
                        )
                        time.sleep(delay)
                    else:
                        logging.error('Все %s попыток неудачны', max_attempts)
                        raise last_exception
            return None
        return wrapper
    return decorator
