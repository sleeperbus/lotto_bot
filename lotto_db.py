import pymongo
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

host = config['DB']['HOST']
username = config['DB']['USERNAME']
password = config['DB']['PASSWORD']
authSource = config['DB']['AUTHSOURCE']


dbconn = pymongo.MongoClient(
    host, username=username, password=password, authSource=authSource)
db = dbconn['lotto']


def insertRoundWinInfo(round, round_date, numbers, bonus_number, prize):
    """
    회차의 정보를 db에 생성한다.
    """
    db.round_win_info.update({'round': round}, {'round_date': round_date, 'numbers': numbers, 'bonus_number': bonus_number, 'prize': prize}, upsert=True)
    #db.round_win_info.insert_one(p_round)


def upsertBuyInfo(user_id, round, numbers):
    """구입한 로또의 정보를 기록한다."""
    db.buy_info.update({'user_id': user_id, 'round': round}, {'$push': {'numbers': {'$each': numbers}}}, upsert=True)

        
def getRoundBuyInfo(user_id, round):
    return db.buy_info.find_one({'user_id': user_id, 'round': round})


def getRoundWinInfo(round):
    """
    회차의 정보를 반환한다.
    """
    return db.round_win_info.find_one({'round': round})


if __name__ == '__main__':
    import pprint
    for item in db.rounds.find():
        pprint.pprint(item)