import requests

URL_DJANGO = 'http://194.58.92.160:8001/api/'


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
# res_delete = {
#                 'id' : [1,2,3],
#                 'tg_id' : 1893883161
#             }

# req = requests.post(URL_DJANGO + 'delete/kf/recipient/', json=res_delete)
# print(req.status_code)
