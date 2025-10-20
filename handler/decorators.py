import functools
import logging
import time
from datetime import datetime as dt
from http.client import IncompleteRead

import requests

from handler.constants import DATE_FORMAT, TIME_FORMAT
from handler.logging_config import setup_logging

setup_logging()


def time_of_script(func):
    """Декортаор для измерения времени работы всего приложения."""
    @functools.wraps(func)
    def wrapper():
        date_str = dt.now().strftime(DATE_FORMAT)
        time_str = dt.now().strftime(TIME_FORMAT)
        run_id = str(int(time.time()))
        print(f'Функция main начала работу {date_str} в {time_str}')
        start_time = time.time()
        try:
            result = func()
            execution_time = round(time.time() - start_time, 3)
            print(
                'Функция main завершила '
                f'работу в {dt.now().strftime(TIME_FORMAT)}.'
                f' Время выполнения - {execution_time} сек. '
                f'или {round(execution_time / 60, 2)} мин.'
            )
            logging.info('SCRIPT_FINISHED_STATUS=SUCCESS')
            logging.info('DATE=%s', date_str)
            logging.info('EXECUTION_TIME=%s сек', execution_time)
            logging.info('FUNCTION_NAME=%s', func.__name__)
            logging.info('RUN_ID=%s', run_id)
            logging.info('ENDLOGGING=1')
            return result
        except Exception as e:
            execution_time = round(time.time() - start_time, 3)
            print(
                'Функция main завершилась '
                f'с ошибкой в {dt.now().strftime(TIME_FORMAT)}. '
                f'Время выполнения - {execution_time} сек. '
                f'Ошибка: {e}'
            )
            logging.info('SCRIPT_FINISHED_STATUS=ERROR')
            logging.info('DATE=%s', date_str)
            logging.info('EXECUTION_TIME=%s сек', execution_time)
            logging.info('ERROR_TYPE=%s', type(e).__name__)
            logging.info('ERROR_MESSAGE=%s', str(e))
            logging.info('FUNCTION_NAME=%s', func.__name__)
            logging.info('RUN_ID=%s', run_id)
            logging.info('ENDLOGGING=1')
            raise
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
