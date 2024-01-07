import json
import re
import requests

class DisneyPlusLogin:
    def __init__(self, email, password, proxies=None):
        self.email = email
        self.password = password
        self.web_page = 'https://www.disneyplus.com/login'
        self.devices_url = "https://global.edge.bamgrid.com/devices"
        self.login_url = 'https://global.edge.bamgrid.com/idp/login'
        self.token_url = "https://global.edge.bamgrid.com/token"
        self.grant_url = 'https://global.edge.bamgrid.com/accounts/grant'
        self.session = requests.Session()
        if proxies:
            self.session.proxies.update(proxies)

    def _get_client_api_key(self):
        response = self.session.get(self.web_page)
        match = re.search("window.server_path = ({.*});", response.text)
        json_data = json.loads(match.group(1))
        return json_data["sdk"]["clientApiKey"]

    def _get_assertion(self, client_api_key):
        headers = {"Authorization": f"Bearer {client_api_key}", "Origin": "https://www.disneyplus.com"}
        post_data = {
            "applicationRuntime": "firefox",
            "attributes": {},
            "deviceFamily": "browser",
            "deviceProfile": "macosx"
        }
        response = self.session.post(url=self.devices_url, headers=headers, json=post_data)
        return response.json()["assertion"]

    def _get_access_token(self, client_api_key, assertion):
        headers = {"Authorization": f"Bearer {client_api_key}", "Origin": "https://www.disneyplus.com"}
        post_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "latitude": "0",
            "longitude": "0",
            "platform": "browser",
            "subject_token": assertion,
            "subject_token_type": "urn:bamtech:params:oauth:token-type:device"
        }
        response = self.session.post(url=self.token_url, headers=headers, data=post_data)

        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            self._handle_error(response)

    def _handle_error(self, response):
        try:
            error_message = response.json().get("errors", {}).get('error_description', response.text)
        except json.JSONDecodeError:
            error_message = response.text
        print(f'Error: {error_message}')
        exit()

    def _login(self, access_token):
        headers = self._get_headers(access_token)
        data = {'email': self.email, 'password': self.password}
        response = self.session.post(url=self.login_url, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            return response.json()["id_token"]
        else:
            self._handle_error(response)

    def _get_headers(self, access_token):
        return {
            'Accept': 'application/json; charset=utf-8',
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json; charset=UTF-8',
            'Origin': 'https://www.disneyplus.com',
            'Referer': 'https://www.disneyplus.com/login/password',
            'Sec-Fetch-Mode': 'cors',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'X-Bamsdk-Platform': 'windows',
            'X-Bamsdk-Version': '3.10',
        }

    def _grant(self, id_token, access_token):
        headers = self._get_headers(access_token)
        data = {'id_token': id_token}
        response = self.session.post(url=self.grant_url, data=json.dumps(data), headers=headers)
        return response.json()["assertion"]

    def _get_final_token(self, subject_token, client_api_key):
        headers = {"Authorization": f"Bearer {client_api_key}", "Origin": "https://www.disneyplus.com"}
        post_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "latitude": "0",
            "longitude": "0",
            "platform": "browser",
            "subject_token": subject_token,
            "subject_token_type": "urn:bamtech:params:oauth:token-type:account"
        }
        response = self.session.post(url=self.token_url, headers=headers, data=post_data)

        if response.status_code == 200:
            token_data = response.json()
            return token_data["access_token"], token_data["expires_in"]
        else:
            self._handle_error(response)

    def get_auth_token(self):
        client_api_key = self._get_client_api_key()
        assertion = self._get_assertion(client_api_key)
        access_token = self._get_access_token(client_api_key, assertion)
        id_token = self._login(access_token)
        user_assertion = self._grant(id_token, access_token)
        final_token, expires_in = self._get_final_token(user_assertion, client_api_key)
        return final_token, expires_in
