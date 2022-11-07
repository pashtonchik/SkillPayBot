import requests


def get_adds(jwt: str, host='garantex.io', direction=None, active=None) -> list:
    """direction: sell or buy\n
    active: True or False"""
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    params = {}
    if direction:
        params['direction'] = direction
    if active is not None:
        params['active'] = active

    url = 'https://' + host + '/api/v2/otc/my/ads'
    ads = requests.get(url, headers=header, params=params)
    if ads.status_code == 200:
        return ads.json()
    else:
        raise Exception('get_adds: status_code != 200', ads.text)


def get_add_detail(jwt, id, host='garantex.io') -> dict:
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    detail = requests.get(
        f'https://{host}/api/v2/otc/ads/{id}', headers=header)
    if detail.status_code == 200:
        return detail.json()
    else:
        raise Exception('get_add_detail: status_code != 200', detail.text)


def edit_add(jwt, id, host='garantex.io', **kwargs) -> dict:
    """min - Минимальная сумма\n
max - Максимальная сумма\n
price - Цена\n
description - Описание\n
payment_method - Способ оплаты\n
active - Активное ли объявление, true или false, по умолчанию false\n
private - Приватное ли объявление, true или false, по умолчанию false\n
auto_increase - Увеличивать ли максимум объявления до баланса авторизованного пользователя автоматически. true или false, по умолчанию false\n
only_verified - Объявление доступно только верифицированным пользователям. true или false, по умолчанию false\n
rating - Минимальный рейтинг контрагента. NULL, 100, 500 и 1000. По умолчанию - без ограничений"""
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    params = kwargs
    req = requests.put(
        f'https://{host}/api/v2/otc/my/ads/{id}', headers=header, data=params)
    if req.status_code == 200:
        return req.json()
    else:
        raise Exception('edit_add: status_code != 200', req.text)
