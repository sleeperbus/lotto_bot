"""
모든 회차의 로또 정보를 가져와서 DB에 저장한다.
"""
import scraping_lotto as scraping 
import lotto_db as db 
import datetime


lastest_round, lastest_date = scraping.nearestLottoDate(datetime.datetime.now())
if lastest_date.date() > datetime.datetime.now().date():
    lastest_round -= 1

for round in range(1, lastest_round+1):
    print('processing %d round' % round)
    winInfo = scraping.getLottoResult(round)
    db.insertRoundWinInfo(winInfo)

