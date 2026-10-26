"""Native Streamlit widget tests against a real isolated REST/SQLite backend."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from streamlit.testing.v1 import AppTest
from streamlit_client import ApiClient, ApiError

EVIDENCE = []


class StreamlitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_db = os.environ.get('BAANDEE_DB_PATH')
        os.environ['BAANDEE_DB_PATH'] = str(Path(cls.tmp.name)/'ui-test.sqlite3')
        cls.old_endpoint = os.environ.pop('BAANDEE_API_URL', None)

    @classmethod
    def tearDownClass(cls):
        if cls.old_db is None: os.environ.pop('BAANDEE_DB_PATH', None)
        else: os.environ['BAANDEE_DB_PATH'] = cls.old_db
        if cls.old_endpoint is not None: os.environ['BAANDEE_API_URL'] = cls.old_endpoint
        cls.tmp.cleanup()
        (ROOT/'tests/streamlit_test_results.json').write_text(json.dumps(EVIDENCE, ensure_ascii=False, indent=2), encoding='utf-8')

    def record(self, name, input, expected, actual):
        EVIDENCE.append(dict(case=name,input=input,expected=expected,actual=actual,result='PASS' if expected==actual else 'FAIL'))
        self.assertEqual(expected, actual)

    def button(self, app, label):
        return next(button for button in app.button if button.label == label)

    def register(self, username):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'), default_timeout=25).run()
        self.assertEqual(len(app.exception),0)
        app.radio(key='auth_mode').set_value('สมัครสมาชิก').run()
        app.text_input(key='auth_username').set_value(username)
        app.text_input(key='auth_password').set_value('Synthetic-test-123!')
        app.text_input(key='auth_confirm').set_value('Synthetic-test-123!')
        self.button(app,'สร้างบัญชีและเริ่มใช้งาน').click().run()
        self.assertEqual(len(app.exception),0)
        return app

    def test_registration_login_logout(self):
        app=self.register('streamlit_auth')
        self.record('native Streamlit signup','synthetic account','คุณภาพข้อมูลสินค้า',app.title[0].value)
        self.button(app,'ออกจากระบบ').click().run()
        self.assertEqual(len(app.exception),0)
        self.record('logout clears session','logout',False,'user' in app.session_state)
        app.radio(key='auth_mode').set_value('เข้าสู่ระบบ').run()
        app.text_input(key='auth_username').set_value('streamlit_auth')
        app.text_input(key='auth_password').set_value('Synthetic-test-123!')
        self.button(app,'เข้าสู่ระบบ').click().run()
        self.assertEqual(len(app.exception),0)
        self.record('login existing account','synthetic credentials','streamlit_auth',app.session_state['user']['username'])

    def test_add_edit_and_history(self):
        app=self.register('streamlit_products')
        app.radio(key='navigation').set_value('เพิ่มสินค้า').run()
        for label,value in [('รหัสสินค้า','SKU-ST-TEST'),('ชื่อสินค้า','Streamlit test product'),('หมวดหมู่','Kitchen'),('ราคา (บาท)','199')]:
            next(widget for widget in app.text_input if widget.label==label).set_value(value)
        app.text_area[0].set_value('Synthetic UI test creation')
        self.button(app,'เพิ่มสินค้า').click().run()
        self.assertEqual(len(app.exception),0)
        app.radio(key='navigation').set_value('คุณภาพข้อมูลสินค้า').run()
        next(widget for widget in app.text_input if widget.label=='ค้นหาสินค้า').set_value('SKU-ST-TEST').run()
        next(widget for widget in app.text_input if widget.label=='ราคา (บาท)').set_value('249')
        next(widget for widget in app.text_area if widget.label=='เหตุผลการเพิ่มหรือแก้ไข').set_value('Synthetic UI test update')
        self.button(app,'บันทึกและตรวจใหม่').click().run()
        self.assertEqual(len(app.exception),0)
        client=app.session_state['api_client']
        saved=next(r for r in client.call('/api/products')['products'] if r['product_id']=='SKU-ST-TEST')
        self.record('create and edit persist through API','199 then 249','249',saved['unit_price_thb'])
        self.record('audit records update','save reason',True,any('Synthetic UI test update'==h['reason'] for h in client.call('/api/history')))
        # An external update while the edit form is open must not be overwritten.
        next(widget for widget in app.text_input if widget.label=='ราคา (บาท)').set_value('299')
        next(widget for widget in app.text_area if widget.label=='เหตุผลการเพิ่มหรือแก้ไข').set_value('Synthetic stale form')
        external={field:saved[field] for field in ['product_id','product_name','category','unit_price_thb']}
        external.update(unit_price_thb='349',revision=saved['revision'],reason='Synthetic external update')
        client.call('/api/products/'+str(saved['id']),'PUT',external)
        self.button(app,'บันทึกและตรวจใหม่').click().run()
        self.assertEqual(len(app.exception),0)
        actual=next(r for r in client.call('/api/products')['products'] if r['id']==saved['id'])['unit_price_thb']
        self.record('stale Streamlit form cannot overwrite update','299 submitted after external 349','349',actual)

    def test_profile_settings_and_cross_session(self):
        app=self.register('streamlit_profile')
        app.radio(key='navigation').set_value('โปรไฟล์ของฉัน').run()
        next(widget for widget in app.text_input if widget.label=='ชื่อที่แสดง').set_value('Synthetic Quality Team')
        self.button(app,'บันทึกโปรไฟล์').click().run()
        app.radio(key='navigation').set_value('ตั้งค่าบัญชี').run()
        next(widget for widget in app.radio if widget.label=='ขนาดตัวอักษร').set_value('extra-large')
        self.button(app,'บันทึกการตั้งค่า').click().run()
        self.assertEqual(len(app.exception),0)
        self.record('profile persists through REST API','profile save','Synthetic Quality Team',app.session_state['user']['display_name'])
        self.record('font preference persists','extra-large','extra-large',app.session_state['user']['font_size'])
        stranger=ApiClient(app.session_state['api_client'].base_url)
        with self.assertRaises(ApiError) as error: stranger.call('/api/products')
        self.record('sessions isolated','new client without login',401,error.exception.status)

    def test_invalid_login_and_not_found(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=25).run()
        app.text_input(key='auth_username').set_value('does_not_exist')
        app.text_input(key='auth_password').set_value('Wrong-password-123')
        self.button(app,'เข้าสู่ระบบ').click().run()
        self.assertEqual(len(app.exception),0)
        self.record('invalid credentials shown','unknown synthetic user',True,any('ไม่ถูกต้อง' in error.value for error in app.error))
        app=self.register('streamlit_missing')
        with self.assertRaises(ApiError) as error: app.session_state['api_client'].call('/api/missing')
        self.record('API not found handled','GET unknown endpoint',404,error.exception.status)

    def test_service_unavailable(self):
        import socket
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        client=ApiClient('http://127.0.0.1:'+str(port))
        with self.assertRaises(ApiError) as error: client.call('/api/health')
        self.record('unavailable service handled','closed port',503,error.exception.status)


if __name__ == '__main__': unittest.main(verbosity=2)
