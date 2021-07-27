import logging
import os
import time
from logging import LogRecord
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

info_logger = logging.getLogger(__name__)
info_logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5)
info_logger.addHandler(handler)

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
url = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
logger_format = '%(asctime)s, %(levelname)s, %(name)s, %(message)s'

bot = telegram.Bot(token=TELEGRAM_TOKEN)


class TelegramHandler(logging.StreamHandler):

    def emit(self, record: LogRecord) -> None:
        msg = self.format(record)
        send_message(msg)


class JsonError(Exception):

    def __init__(self, key) -> None:
        super().__init__(f'В JSON нет ключа {key}')


def parse_homework_status(homework):
    status = {'reviewing', 'approved', 'rejected'}
    if 'homework_name' not in homework.keys():
        raise JsonError('homework_name')
    if 'status' not in homework.keys():
        raise JsonError('status')
    homework_name = homework['homework_name']
    if homework['status'] not in status:
        raise ValueError('Новый статус домашки')
    if homework['status'] == 'rejected':
        verdict = 'К сожалению, в работе нашлись ошибки.'
    else:
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(url, headers=headers, params=payload)
        return homework_statuses.json()
    except ConnectionError:
        info_logger.exception('Нет связи с сервером')


def send_message(message):
    info_logger.info('Сообщение отправлено')
    return bot.send_message(CHAT_ID, message)


def main():
    current_timestamp = int(time.time())

    logging.basicConfig(
        level=logging.DEBUG,
        filename='my_logger.log',
        format=logger_format
    )

    info_logger.debug('Bot start')

    error_logger = logging.getLogger(__name__)
    error_logger.setLevel(logging.ERROR)
    handler = RotatingFileHandler('my_logger.log', maxBytes=50000000,
                                  backupCount=5)
    error_logger.addHandler(handler)
    telegram_handler = TelegramHandler()
    formatter = logging.Formatter(logger_format)
    telegram_handler.setFormatter(formatter)
    error_logger.addHandler(telegram_handler)

    while True:
        try:
            current_status = get_homeworks(current_timestamp)
            current_status_homework = current_status['homeworks']
            if len(current_status_homework) > 0:
                if current_status_homework[0]['status'] == 'reviewing':
                    time.sleep(20 * 60)
                else:
                    verdict = parse_homework_status(current_status_homework)
                    send_message(verdict)
                    break
            else:
                time.sleep(20 * 60)

        except Exception:
            error_logger.exception('Произошла ошибка')
            time.sleep(5)


if __name__ == '__main__':
    main()
