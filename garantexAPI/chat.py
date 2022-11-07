import requests


def get_all_chats(jwt, host='garantex.io') -> list:
    header = {
        'Authorization': f'Bearer {jwt}'
    }
    chats = requests.get(f'https://{host}/api/v2/otc/chats', headers=header)
    if chats.status_code == 200:
        return chats.json()
    else:
        raise Exception('get_all_chats: status_code != 200', chats.text)


def get_messages_from_chat(jwt, chat_id, host='garantex.io', **kwargs) -> list:
    """chat_id id выбранного чата\n
limit Количество сообщений, по умолчанию - 250\n
offset Сколько первых сообщений пропустить, по умолчанию - 0\n"""

    header = {
        'Authorization': f'Bearer {jwt}'
    }
    messages = requests.get(
        f'https://{host}/api/v2/otc/chats/{chat_id}/messages', headers=header, params=kwargs)
    if messages.status_code == 200:
        return messages.json()
    else:
        raise Exception(
            'get_messages_from_chat: status_code != 200', messages.text)


def send_message(jwt, message, host='garantex.io', **kwargs) -> dict:
    """chat_id - id чата, куда нужно отправить сообщение\n
ad_id - id объявления, в чат которого надо отправить сообщение\n
deal_id - id сделки, в чат которой надо отправить сообщение\n
ОБЯЗАТЕЛЬНО УКАЗАТЬ ОДИН ИЗ ТРЕХ ПАРАМЕТРОВ"""

    header = {
        'Authorization': f'Bearer {jwt}'
    }
    params = kwargs
    message = requests.post(f'https://{host}/api/v2/otc/chats/message')
    if message.status_code == 200:
        return True
    else:
        raise Exception(
            'get_messages_from_chat: status_code != 200', message.text)
