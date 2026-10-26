"""Password hashing and persistent sessions for the shared demo workspace."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from threading import RLock

ITERATIONS = 600_000
SESSION_SECONDS = 12 * 60 * 60


class Auth:
    def __init__(self, store):
        self.store = store
        self.lock = RLock()
        self.attempts = defaultdict(deque)
        with store.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    salt TEXT NOT NULL, password_hash TEXT NOT NULL,
                    iterations INTEGER NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                    expires_at REAL NOT NULL);
            ''')
            # Serialize schema upgrades when local and tunnel servers start together.
            c.execute('BEGIN IMMEDIATE')
            columns = {row['name'] for row in c.execute('PRAGMA table_info(users)')}
            additions = {'display_name': "TEXT NOT NULL DEFAULT ''", 'bio': "TEXT NOT NULL DEFAULT ''",
                         'avatar_color': "TEXT NOT NULL DEFAULT 'purple'", 'font_size': "TEXT NOT NULL DEFAULT 'large'",
                         'default_filter': "TEXT NOT NULL DEFAULT 'all'"}
            for name, definition in additions.items():
                if name not in columns:
                    c.execute(f'ALTER TABLE users ADD COLUMN {name} {definition}')

    def account(self, user_id):
        with self.store.connect() as c:
            row = c.execute('SELECT id,username,display_name,bio,avatar_color,font_size,default_filter,created_at FROM users WHERE id=?', (user_id,)).fetchone()
        return dict(row) if row else None

    def update_profile(self, user_id, payload):
        if not isinstance(payload, dict): raise ValueError('ข้อมูลโปรไฟล์ไม่ถูกต้อง')
        name, bio, color = payload.get('display_name'), payload.get('bio', ''), payload.get('avatar_color', 'purple')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError('ชื่อที่แสดงต้องมี 1–60 ตัวอักษร')
        if not isinstance(bio, str) or len(bio) > 200: raise ValueError('แนะนำตัวได้ไม่เกิน 200 ตัวอักษร')
        if color not in {'purple','blue','green','rose'}: raise ValueError('สีโปรไฟล์ไม่ถูกต้อง')
        with self.store.connect() as c:
            c.execute('UPDATE users SET display_name=?,bio=?,avatar_color=? WHERE id=?', (name.strip(), bio.strip(), color, user_id))
        return self.account(user_id)

    def update_settings(self, user_id, payload):
        if not isinstance(payload, dict): raise ValueError('ข้อมูลการตั้งค่าไม่ถูกต้อง')
        size, status = payload.get('font_size'), payload.get('default_filter')
        if size not in {'normal','large','extra-large'}: raise ValueError('ขนาดตัวอักษรไม่ถูกต้อง')
        if status not in {'all','pass','error','review','warning'}: raise ValueError('ตัวกรองเริ่มต้นไม่ถูกต้อง')
        with self.store.connect() as c:
            c.execute('UPDATE users SET font_size=?,default_filter=? WHERE id=?', (size, status, user_id))
        return self.account(user_id)

    def change_password(self, user_id, payload, current_token):
        if not isinstance(payload, dict): raise ValueError('ข้อมูลไม่ถูกต้อง')
        current, new, confirm = payload.get('current_password'), payload.get('new_password'), payload.get('confirm_password')
        if not isinstance(current, str) or not 1 <= len(current) <= 128: raise ValueError('กรุณากรอกรหัสผ่านปัจจุบัน')
        if not isinstance(new, str) or not 10 <= len(new) <= 128: raise ValueError('รหัสผ่านใหม่ต้องมี 10–128 ตัวอักษร')
        if new != confirm: raise ValueError('รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน')
        if new == current: raise ValueError('กรุณาใช้รหัสผ่านใหม่ที่ต่างจากรหัสเดิม')
        with self.store.connect() as c:
            user = c.execute('SELECT salt,password_hash,iterations FROM users WHERE id=?', (user_id,)).fetchone()
            if not user or not hmac.compare_digest(self.password_hash(current,user['salt'],user['iterations']),user['password_hash']):
                raise PermissionError('รหัสผ่านปัจจุบันไม่ถูกต้อง')
            salt = secrets.token_hex(16)
            c.execute('UPDATE users SET salt=?,password_hash=?,iterations=? WHERE id=?', (salt,self.password_hash(new,salt),ITERATIONS,user_id))
            c.execute('DELETE FROM sessions WHERE user_id=? AND token_hash!=?', (user_id,self.digest(current_token)))

    def check_rate(self, address):
        with self.lock:
            attempts = self.attempts[address]
            timestamp = time.time()
            while attempts and attempts[0] <= timestamp - 300:
                attempts.popleft()
            if len(attempts) >= 12:
                return False
            attempts.append(timestamp)
            # Bound memory even if many different addresses submit requests.
            if len(self.attempts) > 2000:
                for key in list(self.attempts):
                    if not self.attempts[key] or self.attempts[key][-1] <= timestamp - 300:
                        del self.attempts[key]
                if len(self.attempts) > 2000:
                    self.attempts.pop(next(iter(self.attempts)))
            return True

    @staticmethod
    def password_hash(password, salt, iterations=ITERATIONS):
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), iterations).hex()

    def credentials(self, payload, registering=False):
        if not isinstance(payload, dict):
            raise ValueError('รูปแบบข้อมูลไม่ถูกต้อง')
        username, password = payload.get('username'), payload.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน')
        username = username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', username):
            raise ValueError('ชื่อผู้ใช้ต้องเป็น a-z, 0-9 หรือ _ จำนวน 3–32 ตัว')
        if not 10 <= len(password) <= 128:
            raise ValueError('รหัสผ่านต้องมี 10–128 ตัวอักษร')
        if registering and payload.get('confirm_password') != password:
            raise ValueError('รหัสผ่านทั้งสองช่องไม่ตรงกัน')
        return username, password

    def register(self, payload):
        username, password = self.credentials(payload, True)
        salt = secrets.token_hex(16)
        password_hash = self.password_hash(password, salt)
        try:
            with self.store.connect() as c:
                user_id = c.execute('INSERT INTO users(username,salt,password_hash,iterations,created_at) VALUES (?,?,?,?,?)',
                                    (username, salt, password_hash, ITERATIONS, time.time())).lastrowid
        except sqlite3.IntegrityError:
            raise ValueError('ชื่อผู้ใช้นี้ถูกใช้แล้ว กรุณาเลือกชื่ออื่น')
        return self.account(user_id)

    def login(self, payload):
        username, password = self.credentials(payload)
        with self.store.connect() as c:
            user = c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        # Perform the same work for an unknown user to reduce timing differences.
        candidate = self.password_hash(password, user['salt'] if user else '00' * 16, user['iterations'] if user else ITERATIONS)
        if not user or not hmac.compare_digest(candidate, user['password_hash']):
            raise PermissionError('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
        return self.account(user['id'])

    def session(self, user, old_token=None):
        token = secrets.token_urlsafe(32)
        with self.store.connect() as c:
            c.execute('DELETE FROM sessions WHERE expires_at <= ?', (time.time(),))
            if old_token:
                c.execute('DELETE FROM sessions WHERE token_hash=?', (self.digest(old_token),))
            c.execute('INSERT INTO sessions VALUES (?,?,?)', (self.digest(token), user['id'], time.time() + SESSION_SECONDS))
        return token

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def token(cookie_header):
        try:
            cookie = SimpleCookie()
            cookie.load(cookie_header or '')
            return cookie['bd_session'].value if 'bd_session' in cookie else None
        except Exception:
            return None

    def user(self, token):
        if not token or len(token) > 200:
            return None
        with self.store.connect() as c:
            row = c.execute('SELECT users.id,users.username FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?',
                            (self.digest(token), time.time())).fetchone()
        return self.account(row['id']) if row else None

    def logout(self, token):
        if token:
            with self.store.connect() as c:
                c.execute('DELETE FROM sessions WHERE token_hash=?', (self.digest(token),))
