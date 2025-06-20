import requests
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth("zU4VlPv6mwTL4BtEQN2sLA", "974GnLKXia28o0z1VozbRcUnB31e2A")
headers = {
    "User-Agent": "web:com.yourapp.name:v1.0.0 (by /u/your_reddit_username)",
    "Content-Type": "application/x-www-form-urlencoded"
}
data = {
    "grant_type": "password",
    "username": "OnepieceSolutions",
    "password": "OPSolutions@reddit"
}

response = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
print(response.status_code)
print(response.text)