import requests
from django.conf import settings

PAYU_URLS = {
	"sandbox": "https://secure.snd.payu.com",
	"production": "https://secure.payu.com",
}

class PayUClient:
	def __init__(self):
		self.base_url = PAYU_URLS[settings.PAYU["ENV"]]
		self.client_id = settings.PAYU["CLIENT_ID"]
		self.client_secret = settings.PAYU["CLIENT_SECRET"]
		self.pos_id = settings.PAYU["POS_ID"]

	def get_token(self):
		r = requests.post(
			f"{self.base_url}/pl/standard/user/oauth/authorize",
			data={
				"grant_type": "client_credentials",
				"client_id": self.client_id,
				"client_secret": self.client_secret,
			},
		)
		r.raise_for_status()
		return r.json()["access_token"]

	def create_order(self, *, kwota, opis, email, notify_url, continue_url):
		token = self.get_token()

		data = {
			"notifyUrl": notify_url,
			"continueUrl": continue_url,
			"customerIp": "127.0.0.1",
			"merchantPosId": self.pos_id,
			"description": opis,
			"currencyCode": "PLN",
			"totalAmount": int(kwota * 100),
			"buyer": {"email": email},
			"products": [{
				"name": opis,
				"unitPrice": int(kwota * 100),
				"quantity": 1,
			}],
		}

		r = requests.post(
			f"{self.base_url}/api/v2_1/orders",
			json=data,
			headers={"Authorization": f"Bearer {token}"},
		)
		r.raise_for_status()
		return r.json()
