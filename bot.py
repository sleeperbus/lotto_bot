# -*- coding: utf-8 -*-
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from pyzbar import pyzbar
import cv2
import logging
import configparser
import re
import lotto_db as db
import scraping_lotto as scraping
import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

QR_FOLDER_PATH = 'QR_PHOTO_DOWNLOAD'


def lottoPhoto(bot, update):
    """
    사용자가 업로드한 이미지에서 바코드를 찾는다.
    """
    user = update.message.from_user
    photo_file = bot.get_file(update.message.photo[-1].file_id)
    dl_file_name = "{}/{}_{}".format(QR_FOLDER_PATH,
                                     user.id, photo_file.file_id)
    photo_file.download(dl_file_name)
    logger.info('photo of %s: %s', user.id, dl_file_name)

    barcodes = extractBarcodes(dl_file_name)
    barcodes = [barcode for barcode in barcodes if barcode.startswith(
        r'http://qr.645lotto.net')]
    if barcodes:
        lotto_dict = buyInfoFromUrl(barcodes[0])
        lotto_dict['user_id'] = user.id
        if lotto_dict:
            update.message.reply_text('구입회차: %s' % lotto_dict['round'])
            update.message.reply_text(
                '\n'.join([','.join(number) for number in lotto_dict['numbers']]))
            db.upsertBuyInfo(
                lotto_dict['user_id'], lotto_dict['round'], lotto_dict['numbers'])
        else:
            update.message.reply_text('이미지에서 로또 번호를 찾을 수 없습니다.')
    else:
        update.message.reply_text('이미지에서 웹주소가 포함된 바코드를 찾을 수 없습니다.')

def strRoundWinInfo(round):
    """
    당첨결과를 텍스트로 반환한다.
    """
    winInfo = db.getRoundWinInfo(round)
    

def getRoundInfo(bot, update, args):
    """
    사용자가 구입한 로또 정보를 보여준다.
    당첨 결과가 있다면 그것도 가져온다.
    """
    try:
        round = int(args[0])
        buy_info = db.getRoundBuyInfo(update.message.chat_id, round)
        # logger.info('buy round info: %s', buy_info)
        return_message = """
        {}회차에는 {}건의 구매정보가 있습니다.
        {}
        """.format(update.message.text, len(buy_info['numbers']), '\n'.join([', '.join(item) for item in buy_info['numbers']]))
        update.message.reply_text(return_message)
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /round <로또회차>")




def buyInfoFromUrl(url):
    """
    사진에서 추출한 url을 분석한다. url 은 아래와 같은 모습이다.
    http://qr.645lotto.net/?v=0834m030515182131q062123273437q060711161823n000000000000n0000000000000000001475
    """
    if not url.startswith('http'):
        return
    # 마지막 10자리는... 무슨 숫자인지 모르겠다.
    # 연속된 12자리를 잡아낸다. 00 시작되는 숫자열은 구매하지 않은 임시 번호들이므로 제거한다.
    url = url[:-10]
    round = int(re.findall(r'v=[0-9]{4}', url)[0].replace(r'v=', ''))

    numbers = re.findall('[0-9]{12}', url)
    numbers = [number for number in numbers if not number.startswith('00')]

    purchase_numbers = []
    for number in numbers:
        number_onegame = []
        while number:
            one_digit = number[:2]
            number = number[2:]
            number_onegame.append(one_digit)
        purchase_numbers.append(number_onegame)
    return {'round': round, 'numbers': purchase_numbers}


def weeklyLottoResult(bot, job):
    """
    해당 회차의 당첨 정보를 가져와서 DB 에 생성한다.
    """
    (lotto_round, lotto_date) = scraping.nearestLottoDate(datetime.datetime.now())
    winInfo = scraping.getLottoResult(lotto_round)
    logger.info('winInfo: %s' % winInfo)
    message = "{}회의 당첨번호는 다음과 같습니다.\n{}".format(winInfo['round'], winInfo['numbers'])
    db.insertRoundWinInfo(winInfo['round'], winInfo['round_date'],
                          winInfo['numbers'], winInfo['bonus_number'], winInfo['prize'])
    bot.send_message(job.context, message)


def extractBarcodes(file):
    """이미지에서 바코드를 찾아낸다."""
    result = list()
    image = cv2.imread(file)
    barcodes = pyzbar.decode(image)

    for barcode in barcodes:
        barcodeData = barcode.data.decode('utf-8')
        result.append(barcodeData)
    return result


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warn('Update "%s" caused "%s"', update, error)


def main():
    # 사용자 정보를 불러온다.
    config = configparser.ConfigParser()
    config.read('config.ini')

    # 핸들러 등록
    updater = Updater(config['TELEGRAM']['TOKEN'])
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.photo, lottoPhoto))
    # dp.add_handler(MessageHandler(Filters.text, getRoundInfo))
    dp.add_handler(CommandHandler('round', getRoundInfo, pass_args=True))
    dp.add_error_handler(error)

    # 배치 잡
    j = updater.job_queue
    job_weekly = j.run_daily(weeklyLottoResult, datetime.time(20, 55), days=(6,), context=config['SUPERUSER'])
    # job_weekly = j.run_once(weeklyLottoResult, 5, context=1)

    # idling
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()