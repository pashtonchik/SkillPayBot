import requests


r = requests.get('http://194.58.92.160:8000/api/trades/active/')

print(r.text)