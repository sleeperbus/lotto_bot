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
import time
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

QR_FOLDER_PATH = 'QR_PHOTO_DOWNLOAD'


def lottoPhoto(bot, update):
    """
    사용자가 업로드한 이미지에서 바코드를 찾는다.
    836회부터 웹주소가 바뀌었다.
    """
    user = update.message.from_user
    photo_file = bot.get_file(update.message.photo[-1].file_id)
    dl_file_name = "{}/{}_{}".format(QR_FOLDER_PATH,
                                     user.id, photo_file.file_id)
    photo_file.download(dl_file_name)
    logger.info('photo of %s: %s', user.id, dl_file_name)

    barcodes = extractBarcodes(dl_file_name)
    barcodes = [barcode for barcode in barcodes
                if (barcode.startswith(r'http://qr.645lotto.net') or barcode.startswith(r'http://m.dhlottery.co.kr'))]
    if barcodes:
        # 사진 하나에는 하나의 제품 바코드만 있다.
        buyInfo = buyInfoFromUrl(barcodes[0])
        buyInfo['user_id'] = user.id
        logger.info('new lotto: %s', buyInfo)
        if buyInfo:
            update.message.reply_text(strBuyInfo(buyInfo))
            db.upsertBuyInfo(buyInfo)
            winInfo = db.getRoundWinInfo(buyInfo['round'])
            if winInfo:
                update.message.reply_text(strRoundWinInfo(winInfo))
                update.message.reply_text(strMyWinResult(buyInfo, winInfo))
            else:
                update.message.reply_text(
                    "{}회차의 당첨 정보가 없습니다. 곧 알려드리겠습니다.".format(buyInfo['round']))
        else:
            update.message.reply_text('이미지에서 로또 번호를 찾을 수 없습니다.')
    else:
        update.message.reply_text('이미지에서 웹주소가 포함된 바코드를 찾을 수 없습니다.')

    # 사진은 바로 삭제한다.
    os.unlink(dl_file_name)
    

def strBuyInfo(info):
    return "{}회차에는 {}건의 구매정보가 있습니다.\n{}".format(info['round'],
                                                len(info['numbers']),
                                                '\n'.join([', '.join(item) for item in info['numbers']]))


def strRoundWinInfo(winInfo):
    """해당 라운드의 로또 결과를 출력한다."""
    win_numbers = winInfo['numbers']
    win_bonus_number = winInfo['bonus_number']
    prize = winInfo['prize']
    message = "당첨번호: {} + {}\n{}".format(
        ",".join(win_numbers), win_bonus_number,
        "\n".join(["{}등: {:,}원".format(i, prize[str(i)][1]) for i in range(1, 6)]))
    return message


def strMyWinResult(buyInfo, winInfo):
    """
    당첨번호와 구입한 복권의 번호를 비교해서 당첨 정보를 반환한다.
    (등수,맞은 번호)의 리스트를 반환한다. 
    """
    buy_numbers = buyInfo['numbers']
    prize = winInfo['prize']
    win_numbers = winInfo['numbers']
    win_bonus_number = winInfo['bonus_number']

    right_numbers = zip(buy_numbers, [
                        [number for number in numbers if number in win_numbers] for numbers in buy_numbers])
    result = []
    for i, match_numbers in enumerate(right_numbers):
        if len(match_numbers[1]) == 6:
            result.append("1등!! 상금 {:,}원, {}".format(
                prize[str(1)][1], ", ".join(match_numbers[1])))
        elif len(match_numbers[1]) == 5:
            if win_bonus_number in match_numbers[0]:
                result.append(
                    "2등!! 상금 {:,}원, {}+{}".format(prize[str(2)][1], ", ".join(match_numbers[1]), win_bonus_number))
            else:
                result.append((3, match_numbers[1]))
                result.append("3등!! 상금 {:,}원, {}".format(
                    prize[str(3)][1], ", ".join(match_numbers[1])))
        elif len(match_numbers[1]) == 4:
            result.append("4등!! 상금 {:,}원, {}".format(
                prize[str(4)][1], ", ".join(match_numbers[1])))
        elif len(match_numbers[1]) == 3:
            result.append("5등!! 상금 {:,}원, {}".format(
                prize[str(4)][1], ", ".join(match_numbers[1])))

    return '\n'.join(result) if result else '아쉽게도 이번에는 당첨내용이 없습니다.'


def getRoundInfo(bot, update, args):
    """
    사용자가 구입한 로또 정보를 보여준다.
    당첨 결과가 있다면 그것도 가져온다.
    """
    try:
        round = int(args[0])
        buy_info = db.getRoundBuyInfo(update.message.chat_id, round)
        win_info = db.getRoundWinInfo(round)

        if buy_info:
            update.message.reply_text(strBuyInfo(buy_info))
        if win_info:
            update.message.reply_text(strRoundWinInfo(win_info))
        if win_info and buy_info:
            update.message.reply_text(strMyWinResult(buy_info, win_info))

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


def extractBarcodes(file):
    """이미지에서 바코드를 찾아낸다."""
    result = list()
    image = cv2.imread(file)
    barcodes = pyzbar.decode(image)

    for barcode in barcodes:
        barcodeData = barcode.data.decode('utf-8')
        result.append(barcodeData)
    return result


def sendWinInfoToAllUsers(bot, round, winInfo):
    """해당 회차를 구입한 모든 사람들에게 당첨 정보를 보낸다."""
    allBuyInfo = db.getAllRoundBuyInfo(round)
    # 아직 당첨 정보가 들어오지 않았다면 대기한다.
    msgWinInfo = strRoundWinInfo(winInfo)
    for buyInfo in allBuyInfo:
        msgUserWinInfo = strMyWinResult(buyInfo, winInfo)
        msgBuyInfo = strBuyInfo(buyInfo)
        bot.send_message(buyInfo['user_id'], "\n".join(
            [msgBuyInfo, msgWinInfo, msgUserWinInfo]))


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warn('Update "%s" caused "%s"', update, error)


def weeklyLottoResult(bot, job):
    """
    해당 회차의 당첨 정보를 가져와서 DB 에 생성한다.
    """
    (lotto_round, lotto_date) = scraping.nearestLottoDate(datetime.datetime.now())
    win_info = scraping.getLottoResult(lotto_round)
    # 당첨 결과를 가지고 오기를 계속 시도한다.
    while not win_info:
        time.sleep(20)
        win_info = scraping.getLottoResult(lotto_round)
    logger.info('win_info: %s' % win_info)
    message = "{}회의 당첨번호는 다음과 같습니다.\n{}".format(
        win_info['round'], win_info['numbers'])
    db.insertRoundWinInfo(win_info)
    bot.send_message(job.context, message)


def weeklySendWinInfo(bot, job):
    """당첨정보를 유저들에게 보낸다."""
    (lotto_round, lotto_date) = scraping.nearestLottoDate(datetime.datetime.now())
    winInfo = db.getRoundWinInfo(lotto_round)

    # 추첨 정보가 없으면 대기를 한다.
    tryCount = 0
    while not winInfo:
        logger.info("당첨 정보를 찾지 못했습니다. trying: {}...".format(tryCount))
        time.sleep(60)
        winInfo = db.getRoundWinInfo(lotto_round)
        tryCount += 1
        if tryCount == 3:
            tryCount = 0
            bot.send_message(job.context, "당첨정보가 없어 유저들에게 메세지를 보내지 못하고 있습니다.")

    s_time = datetime.datetime.now()
    sendWinInfoToAllUsers(bot, lotto_round, winInfo)
    e_time = datetime.datetime.now()
    bot.send_message(job.context, "당첨정보를 보내는데 {:,}초 걸렸습니다.".format(
        (e_time - s_time).seconds))


def dailyUrlCheck(bot, job):
    """로또 사이트에서 결과를 가져올 수 있는지 확인한다."""
    if not scraping.getLottoResult(1):
        bot.send_message(job.context, "daily: 로또 사이트에서 당첨 결과를 가져올 수 없습니다.")
        
def weeklyCheerupBuyLotto(bot, job):
    """로또를 구매하지 않은 사람에게 구매를 격려한다."""
    (lotto_round, lotto_date) = scraping.nearestLottoDate(datetime.datetime.now())
    users = db.getUsersNotBuyRound(lotto_round)
    for user in users:
        bot.send_message(user['user_id'], "{0}회차 로또를 아직 구입하지 않았네요. 이번에는 잘 될지도 모르잖아요...".format(lotto_round))
    bot.send_message(job.context, "독려 메세지 전송을 완료했습니다.")


def main():
    # 사용자 정보를 불러온다.
    config = configparser.ConfigParser()
    config.read('config.ini')

    # 핸들러 등록
    updater = Updater(config['TELEGRAM']['TOKEN'])
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.photo, lottoPhoto))
    dp.add_handler(CommandHandler('round', getRoundInfo, pass_args=True))
    dp.add_error_handler(error)

    # 배치 잡
    j = updater.job_queue
    j.run_daily(weeklyLottoResult, datetime.time(20, 55),
                days=(5,), context=config['TELEGRAM']['SUPERUSER'])
    j.run_daily(weeklySendWinInfo, datetime.time(21, 00),
                days=(5,), context=config['TELEGRAM']['SUPERUSER'])
    j.run_daily(dailyUrlCheck, datetime.time(8, 30), context=config['TELEGRAM']['SUPERUSER'])
    j.run_daily(weeklyCheerupBuyLotto, datetime.time(18,00), days=(4,), context=config['TELEGRAM']['SUPERUSER'])
    j.run_daily(weeklyCheerupBuyLotto, datetime.time(16,00), days=(5,), context=config['TELEGRAM']['SUPERUSER'])

    # 봇 시작
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
