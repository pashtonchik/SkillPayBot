import requests


def get_trades(jwt, host='garantex.io', **kwargs) -> list:
    """currency	Код фиатной валюты. Например, rub, uah, usd \n
    state Фильтрация по статусу сделки. pending, waiting, paid, arbitration, canceled, completed. Если статус не задан, выводятся все активные сделки\n
    counterparty Nickname второго участника сделки\n
    direction Направление сделки - sell, buy. По умолчанию выводятся все.\n
    limit Количество сделок, по умолчанию - 250\n
    offset Через сколько первых сделок начать выводить остальные сделки\n
    start_time Время создания сделок, нижняя граница. Без ограничений (date-time)\n
    end_time Время создания сделок, верхняя граница. Ограничение - текущий момент (date-time)\n
    order_by Сортировка по id, asc или desc, по умолчанию desc
    """
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    params = kwargs
    url = 'https://' + host + '/api/v2/otc/deals'
    trades = requests.get(url=url, headers=header, params=params)
    if trades.status_code == 200:
        return trades.json()
    else:
        raise Exception('get_trades: status_code != 200', trades.text)


def get_trade_detail(jwt, id, host='garantex.io') -> dict:
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    detail = requests.get(
        f'https://{host}/api/v2/otc/deals/{id}', headers=header)
    if detail.status_code == 200:
        return detail.json()
    else:
        raise Exception('get_trade_detail: status_code != 200', detail.text)


def close_trade(jwt, id, host='garantex.io') -> bool:
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    req = requests.put(
        f'https://{host}/api/v2/otc/deals/{id}/complete', headers=header)
    if req.status_code == 200:
        return True
    else:
        raise Exception('close_trade: status_code != 200', req.text)


def cancel_trade(jwt, id, host='garantex.io') -> bool:
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    req = requests.put(
        f'https://{host}/api/v2/otc/deals/{id}/cancel', headers=header)
    if req.status_code == 200:
        return True
    else:
        raise Exception('cancel_trade: status_code != 200', req.text)


def accept_trade(jwt, id, host='garantex.io') -> dict:
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    req = requests.put(
        f'https://{host}/api/v2/otc/deals/{id}/accept', headers=header)
    if req.status_code == 200:
        return req.json()
    else:
        raise Exception('accept_trade: status_code != 200', req.text)
