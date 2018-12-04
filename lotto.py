from bs4 import BeautifulSoup
import re
from urllib.request import urlopen
import sys
import datetime

first_lotto_date = datetime.date(2002, 12, 7)


def lottoDate(p_num):
    """
    각 회차의 로또 날짜를 가져온다.
    """
    return first_lotto_date + datetime.timedelta(days=(int(p_num) - 1) * 7)


def nearestLottoDate(p_date):
    """
    해당 일자의 가장 가까운 로또 회차 정보를 가져온다.
    """
    dateInfo = p_date + datetime.timedelta((12 - p_date.weekday()) % 7)
    roundInfo = int(((dateInfo - first_lotto_date).days / 7) + 1)
    return (roundInfo, dateInfo)


def getLottoResult(p_num):
    """
    각 회차의 로또 결과를 dictionary로 반환한다.
    """
    url = 'http://www.nlotto.co.kr/gameResult.do?method=byWin&drwNo={}'.format(
        p_num)
    html = urlopen(url)
    bsObj = BeautifulSoup(html.read(), "html.parser")
    images = bsObj.find_all(
        "img", {"src": re.compile(".*ball_[0-9]{1,2}\.png")})
    resultDict = dict(
        round=p_num, round_date=(lottoDate(p_num)).strftime("%Y%m%d"), numbers={})
    for i, image in enumerate(images):
        resultDict['numbers'][str(i + 1)] = image['alt']
    return resultDict


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(getLottoResult(sys.argv[1]))
    else:
        num_831 = getLottoResult(831)
        print(num_831)
