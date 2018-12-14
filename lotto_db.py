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


def insertRoundWinInfo(info):
    """
    회차의 정보를 db에 생성한다.
    """
    db.round_win_info.update({'round': info['round']}, {'round': info['round'], 'round_date': info['round_date'],
                                                        'numbers': info['numbers'], 'bonus_number': info['bonus_number'], 'prize': info['prize']}, upsert=True)

def upsertBuyInfo(info):
    """구입한 로또의 정보를 기록한다."""
    db.buy_info.update({'user_id': info['user_id'], 'round': info['round']}, {
                       '$push': {'numbers': {'$each': info['numbers']}}}, upsert=True)
    db.user_rounds.update({'user_id': info['user_id']}, {'$addToSet': {'rounds': info['round']}}, upsert=True)


def getRoundBuyInfo(user_id, round):
    """해당 유저의 구입 정보를 반환한다."""
    return db.buy_info.find_one({'user_id': user_id, 'round': round})

        
def getAllRoundBuyInfo(round):
    return db.buy_info.find({'round': round})


def getRoundWinInfo(round):
    """
    회차의 정보를 반환한다.
    """
    return db.round_win_info.find_one({'round': round})
    
def getUsersNotBuyRound(round):
    """해당 회차를 구매하지 않은 사람들 정보를 가져온다."""
    return  db.user_rounds.find({'rounds': {'$nin': [round]}})


if __name__ == '__main__':
    import pprint
    for item in db.rounds.find():
        pprint.pprint(item)
