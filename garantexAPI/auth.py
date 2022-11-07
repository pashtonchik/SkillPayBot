import base64
import time
import datetime
import random
import requests
import jwt


def get_jwt(private_key: str, uid: str, host='garantex.io') -> str:
    key = base64.b64decode(private_key)
    iat = int(time.mktime(datetime.datetime.now().timetuple()))
    claims = {
        "exp": iat + 1*60*60,  
        "jti": hex(random.getrandbits(12)).upper()
    }
    jwt_token = jwt.encode(claims, key, algorithm="RS256")
    ret = requests.post('https://dauth.' + host + '/api/v1/sessions/generate_jwt',
                        json={'kid': uid, 'jwt_token': jwt_token})
    if ret.status_code == 200:
        token = ret.json().get('token')
        return token
    else:
        raise Exception('get_jwt: status_code != 200', ret.text)
