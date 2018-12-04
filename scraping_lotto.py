from bs4 import BeautifulSoup
import re
from urllib.request import urlopen
import sys
import datetime

first_lotto_date = datetime.datetime(2002, 12, 7)


def lottoDate(round):
    """
    각 회차의 로또 날짜를 가져온다.
    """
    return first_lotto_date + datetime.timedelta(days=(int(round) - 1) * 7)


def nearestLottoDate(inputDate):
    """
    해당 일자의 가장 가까운 로또 회차 정보를 가져온다.
    """
    dateInfo = inputDate + datetime.timedelta((12 - inputDate.weekday()) % 7)
    roundInfo = int(((dateInfo - first_lotto_date).days / 7) + 1)
    return (roundInfo, dateInfo)


def getLottoResult(round):
    """
    각 회차의 로또 결과를 dictionary로 반환한다.
    """
    round_date = (lottoDate(round)).strftime("%Y%m%d")
    numbers = []
    person = []
    payout = []

    # 로또 사이트에서 데이터를 가져온다.
    url = 'https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={}'.format(
        round)
    html = urlopen(url)
    bsObj = BeautifulSoup(html.read(), "html.parser", from_encoding='euc-kr')

    # 당첨 숫자를 추출한다. 마지막 숫자는 보너스 숫자이다.
    # images = bsObj.find_all("img", {"src": re.compile(".*ball_[0-9]{1,2}\.png")})
    # for image in images:
    #     numbers.append(image['alt'].rjust(2, '0'))
    images = bsObj.find_all("span", {"class":"ball_645"})
    for image in images:
        numbers.append(image.get_text().rjust(2, '0'))
    bonus_number = numbers.pop()

    # 당첨금액과 인원을 가져온다.
    payout_table = bsObj.find("table", {"class": "tbl_data"}).find("tbody")
    for item in payout_table.find_all("tr"):
        td_tags = item.find_all("td")
        person.append(int(td_tags[2].get_text().replace(",","")))
        payout.append(int(td_tags[3].get_text().replace(",","").replace("원","")))
    prize = dict(zip(map(str, range(1, len(person) + 1)), zip(person, payout)))


    # payout_table = bsObj.find('table', {'class': 'tblType1'}).find('tbody')
    # for item in payout_table.find_all('tr')[1:-1]:
    #     data = item.find_all('td', {'class': 'rt', 'device': None})
    #     person.append(int(data[0].get_text().replace(',', '')))
    #     payout.append(
    #         int(data[1].get_text().replace(',', '').replace('원', '')))
    # prize = dict(zip(map(str, range(1, len(person) + 1)), zip(person, payout)))

    return {'round': round, 'round_date': round_date, 'numbers': numbers,
            'bonus_number': bonus_number, 'prize': prize}


if __name__ == '__main__':
    import lotto_db
    if len(sys.argv) > 1:
        print(getLottoResult(sys.argv[1]))
    else:
        num_831 = getLottoResult(831)
        print(num_831)
