import requests

URL_DJANGO = 'http://194.58.92.160:8000/api/'


trade_info = {
        'tg_account' : '036',
        'id': 3,
        'card_number': 123456789,
        'source': 'bebz',
        'paymethod': 443,
        'fio': 'bebz',
        'amount': 100,
        'comment': '',
        'type': 'TINK',
        'status': 'trade_created',
    }


a = requests.post(URL_DJANGO + 'create/kf/trade/', json=trade_info)

print(a)