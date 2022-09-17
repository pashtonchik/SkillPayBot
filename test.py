import requests
body = {
        'tg_id': 1893883161
    }
req = requests.post('http://194.58.92.160:8001/api/get_agent_info/', json=body)

print(req.status_code, req.json())