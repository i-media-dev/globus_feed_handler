import functools
import json
import logging
import time
from datetime import datetime as dt
from http.client import IncompleteRead

import requests

from handler.constants import DATE_FORMAT, TIME_FORMAT
from handler.logging_config import setup_logging

setup_logging()


def time_of_script(func):
    """Универсальный декоратор для логирования выполнения."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_ts = time.time()
        date_str = dt.now().strftime(DATE_FORMAT)
        time_str = dt.now().strftime(TIME_FORMAT)
        print(f'Функция main начала работу {date_str} в {time_str}')

        try:
            result = func(*args, **kwargs)
            status = 'SUCCESS'
            error_type = error_message = None
        except Exception as e:
            status = 'ERROR'
            error_type, error_message = type(e).__name__, str(e)
            result = None

        exec_time_min = round((time.time() - start_ts) / 60, 2)
        exec_time_sec = round(time.time() - start_ts, 3)
        print(
            'Функция main завершила '
            f'работу в {dt.now().strftime(TIME_FORMAT)}.'
            f' Время выполнения - {exec_time_min} мин. '
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

        if status == "ERROR":
            raise

        return result

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


def retry_on_network_error(max_attempts=3, delays=(2, 5, 10)):
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
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ReadTimeout
                ) as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = delays[attempt - 1] if attempt - \
                            1 < len(delays) else delays[-1]
                        logging.warning(
                            'Попытка %s/%s неудачна, повтор через %s сек: %s',
                            attempt, max_attempts, delay, e)
                        time.sleep(delay)
                    else:
                        logging.error('Все %s попыток неудачны', max_attempts)
                        raise last_exception
            return None
        return wrapper
    return decorator
