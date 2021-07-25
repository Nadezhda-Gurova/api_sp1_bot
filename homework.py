import logging
import os
import time
from logging import LogRecord
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)


class TelegramHandler(logging.StreamHandler):

    def emit(self, record: LogRecord) -> None:
        msg = self.format(record)
        send_message(msg)


def parse_homework_status(homework):
    homework_name = homework['homework_name']
    if homework['status'] == 'rejected':
        verdict = 'К сожалению, в работе нашлись ошибки.'
    else:
        verdict = 'Ревьюеру всё понравилось, работа зачтена!'
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homeworks(current_timestamp):
    url = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    homework_statuses = requests.get(url, headers=headers, params=payload)
    return homework_statuses.json()


def send_message(message):
    logging.info('Сообщение отправлено')
    return bot.send_message(CHAT_ID, message)


def main():
    logger_format = '%(asctime)s, %(levelname)s, %(name)s, %(message)s'
    current_timestamp = int(time.time())

    logging.basicConfig(
        level=logging.DEBUG,
        filename='my_logger.log',
        format=logger_format
    )
    logging.debug('Bot start')

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
            if current_status['homeworks'][0]['status'] == 'reviewing':
                time.sleep(5 * 60)  # Опрашивать раз в пять минут
            else:
                verdict = parse_homework_status(current_status['homeworks'][0])
                send_message(verdict)
                break

        except Exception as e:
            error_logger.exception('Произошла ошибка')
            print(f'Бот упал с ошибкой: {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()
