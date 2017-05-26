import json
import requests

url = 'https://data.sbb.ch/api/records/1.0/search/'
params = {
    'dataset': 'ist-daten-sbb',
    'rows': 1,
}
response = requests.get(url, params)

data = response.json()
print(data)
