import requests

class Line:
    LINE_NOTIFY_URL = 'https://notify-api.line.me/api/notify'
    def __init__(self, token):
        self.line_notify_token = token

    def send_message(self, message):
        headers = {'Authorization' : 'Bearer ' + self.line_notify_token}
        payload = {'message' : message}

        response = requests.post(self.LINE_NOTIFY_URL, headers = headers, params = payload)
        return response
