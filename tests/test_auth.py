import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import Store
from auth import Auth

class AuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'auth.sqlite3')
        self.auth=Auth(self.store)
        self.payload=dict(username='test_user',password='synthetic-password-123',confirm_password='synthetic-password-123')
    def tearDown(self): self.tmp.cleanup()
    def test_hash_storage(self):
        self.auth.register(self.payload)
        with self.store.connect() as c: row=dict(c.execute('SELECT * FROM users').fetchone())
        self.assertNotIn(self.payload['password'],str(row))
        self.assertEqual(len(row['salt']),32)
        self.assertEqual(row['iterations'],600000)
    def test_duplicate_and_validation(self):
        self.auth.register(self.payload)
        with self.assertRaises(ValueError): self.auth.register(dict(self.payload,username='TEST_USER'))
        with self.assertRaises(ValueError): self.auth.register(dict(self.payload,password='short'))
        with self.assertRaises(ValueError): self.auth.register(dict(self.payload,confirm_password='not-matching'))
    def test_session_expiry_rotation_and_persistence(self):
        user=self.auth.register(self.payload)
        token=self.auth.session(user)
        self.assertEqual(Auth(Store(self.store.db)).user(token)['username'],'test_user')
        new_token=self.auth.session(user,token)
        self.assertIsNone(self.auth.user(token))
        with self.store.connect() as c: c.execute('UPDATE sessions SET expires_at=0')
        self.assertIsNone(self.auth.user(new_token))
    def test_rate_limit(self):
        for _ in range(12): self.assertTrue(self.auth.check_rate('test-client'))
        self.assertFalse(self.auth.check_rate('test-client'))
    def test_logout_and_random_session(self):
        user=self.auth.register(self.payload)
        token=self.auth.session(user)
        self.assertIsNone(self.auth.user('made-up-token'))
        self.auth.logout(token)
        self.assertIsNone(self.auth.user(token))
    def test_profile_and_settings_are_per_account(self):
        first=self.auth.register(self.payload)
        second=self.auth.register(dict(self.payload,username='other_user'))
        self.auth.update_profile(first['id'],dict(display_name='Quality Team',bio='Synthetic profile',avatar_color='blue',user_id=second['id']))
        self.auth.update_settings(first['id'],dict(font_size='extra-large',default_filter='review'))
        reopened=Auth(Store(self.store.db))
        self.assertEqual(reopened.account(first['id'])['display_name'],'Quality Team')
        self.assertEqual(reopened.account(first['id'])['font_size'],'extra-large')
        self.assertEqual(reopened.account(first['id'])['default_filter'],'review')
        self.assertEqual(reopened.account(second['id'])['display_name'],'')
        self.assertEqual(reopened.account(second['id'])['font_size'],'large')
    def test_profile_validation(self):
        user=self.auth.register(self.payload)
        for profile in [dict(display_name='',bio='',avatar_color='blue'),dict(display_name='test',bio='x'*201,avatar_color='blue'),dict(display_name='test',avatar_color='invalid')]:
            with self.assertRaises(ValueError): self.auth.update_profile(user['id'],profile)
        with self.assertRaises(ValueError): self.auth.update_settings(user['id'],dict(font_size='tiny',default_filter='all'))
    def test_concurrent_schema_upgrade(self):
        legacy_store=Store(Path(self.tmp.name)/'legacy.sqlite3')
        with legacy_store.connect() as c:
            c.execute('CREATE TABLE users (id INTEGER PRIMARY KEY,username TEXT UNIQUE,salt TEXT,password_hash TEXT,iterations INTEGER,created_at REAL)')
        with ThreadPoolExecutor(max_workers=2) as pool:
            upgraded=list(pool.map(lambda _:Auth(legacy_store),range(2)))
        user=upgraded[0].register(self.payload)
        self.assertEqual(upgraded[1].account(user['id'])['font_size'],'large')
    def test_password_change_revokes_other_sessions(self):
        user=self.auth.register(self.payload)
        current=self.auth.session(user)
        other=self.auth.session(user)
        with self.assertRaises(PermissionError):
            self.auth.change_password(user['id'],dict(current_password='wrong-password',new_password='new-test-password',confirm_password='new-test-password'),current)
        self.auth.change_password(user['id'],dict(current_password=self.payload['password'],new_password='new-test-password',confirm_password='new-test-password'),current)
        self.assertIsNone(self.auth.user(other))
        self.assertIsNotNone(self.auth.user(current))
        with self.assertRaises(PermissionError): self.auth.login(self.payload)
        self.assertEqual(self.auth.login(dict(self.payload,password='new-test-password'))['id'],user['id'])

if __name__=='__main__': unittest.main(verbosity=2)
