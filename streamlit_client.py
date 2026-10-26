"""Per-browser-session REST client. Never cache this object globally."""
import http.cookiejar
import json
import uuid
import urllib.error
import urllib.request


class ApiError(Exception):
    def __init__(self, message, status=0):
        super().__init__(message)
        self.status = status


class ApiClient:
    def __init__(self, base_url, client_address=None):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_address or 'streamlit-' + uuid.uuid4().hex
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def call(self, path, method='GET', payload=None):
        headers = {'Content-Type': 'application/json', 'CF-Connecting-IP': self.client_id}
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=12) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            try:
                message = json.load(error).get('error', 'API ไม่สามารถดำเนินการได้')
            except (ValueError, AttributeError):
                message = 'API ไม่สามารถดำเนินการได้'
            raise ApiError(message, error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ApiError('เชื่อมต่อ API ไม่ได้ กรุณาตรวจเซิร์ฟเวอร์แล้วลองใหม่', 503) from None
