import sys
import tempfile
import threading
import unittest
import json
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import Store, serve, FIELDS

RESULTS=[]
class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temp.name)/'test.sqlite3')
    def tearDown(self): self.temp.cleanup()
    def record(self,name,input,expected,actual):
        RESULTS.append(dict(case=name,input=input,expected=expected,actual=actual,result='PASS' if expected==actual else 'FAIL'))
        self.assertEqual(expected,actual)
    def test_seed(self):
        self.record('original and synthetic sources','initial database',[82,6],[sum(r['source']==s for r in self.store.rows()) for s in ['original','synthetic-demo']])
    def test_duplicate(self):
        rows=[r for r in self.store.report()['products'] if r['product_id']=='DEMO-003']
        self.record('duplicate ID quarantined','DEMO-003',['error','error'],[r['status'] for r in rows])
    def test_invalid_price(self):
        r=next(r for r in self.store.report()['products'] if r['product_id']=='DEMO-002')
        self.record('negative price','-10',True,any(i['code']=='INVALID_PRICE' for i in r['issues']))
    def test_ambiguous(self):
        self.store.normalize()
        rows=[r for r in self.store.report()['products'] if r['category']=='Bed room']
        self.record('ambiguous category is never guessed','Bed room',True,bool(rows) and all(r['status']=='review' for r in rows))
    def test_alias(self):
        before=next(r for r in self.store.rows() if r['product_id']=='SKU-0019')
        self.store.normalize()
        after=next(r for r in self.store.rows() if r['id']==before['id'])
        history=next(h for h in self.store.history() if h['row_id']==before['id'])
        self.record('safe correction and audit','storage',['Storage','storage'],[after['category'],json.loads(history['before_json'])['category']])
    def test_persistence(self):
        row=self.store.save(dict(product_id='SKU-TEST',product_name='Test',category='Kitchen',unit_price_thb='200',reason='test creation'))
        payload={f:row[f] for f in FIELDS};payload.update(product_name='Updated',revision=row['revision'],reason='test update')
        self.store.save(payload,row['id'])
        reopened=Store(self.store.db)
        actual=next(r for r in reopened.rows() if r['id']==row['id'])
        self.record('create update reopen','new SKU then rename',['Updated',2],[actual['product_name'],len(reopened.history())])
    def test_conflict(self):
        row=self.store.rows()[0];p={f:row[f] for f in FIELDS};p.update(reason='first',revision=row['revision'])
        self.store.save(p,row['id'])
        with self.assertRaises(RuntimeError): self.store.save(p,row['id'])
        self.record('stale update rejected','same revision twice',True,True)
    def test_missing_name(self):
        row=next(r for r in self.store.report()['products'] if r['product_id']=='DEMO-001')
        self.record('missing name','empty product_name',True,any(i['code']=='MISSING_NAME' for i in row['issues']))
    def test_export(self):
        folder=Path(self.temp.name)/'exports'
        before=self.store.report()['summary'].get('pass',0)
        self.store.normalize()
        result=self.store.export(folder)
        with (folder/'products_clean.csv').open(encoding='utf-8-sig') as f:
            import csv
            rows=list(csv.DictReader(f))
        self.record('export separates unresolved records','normalize then export',[78,10,False],[result['clean'],result['quarantine'],any(r['product_id']=='DEMO-003' or r['category']=='Bed room' for r in rows)])
        self.record('before after correction evidence','5 category aliases',5,result['clean']-before)
    def test_api(self):
        server=serve(0,Path(self.temp.name)/'api.sqlite3');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def auth_request(path,payload):
            return client.open(urllib.request.Request(base+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST'))
        try:
            with self.assertRaises(urllib.error.HTTPError) as error: client.open(base+'/api/products')
            self.record('anonymous API blocked','GET products without session',401,error.exception.code)
            with auth_request('/api/auth/register',dict(username='api_tester',password='test-password-123',confirm_password='test-password-123')) as r:
                self.record('registration creates session','new synthetic account',True,'HttpOnly' in r.headers['Set-Cookie'])
            with client.open(base+'/api/products') as r: self.record('API success','GET /api/products',88,json.load(r)['total'])
            with self.assertRaises(urllib.error.HTTPError) as error: client.open(base+'/api/missing')
            self.record('API not found','GET /api/missing',404,error.exception.code)
            payload=dict(product_id='SKU-API',product_name='API test',category='Storage',unit_price_thb='199',reason='API create test')
            req=urllib.request.Request(base+'/api/products',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
            with client.open(req) as r: created=json.load(r)
            payload.update(product_name='API updated',revision=created['revision'],reason='API update test')
            req=urllib.request.Request(base+'/api/products/'+str(created['id']),data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='PUT')
            with client.open(req) as r: self.record('API update','PUT saved record','API updated',json.load(r)['product_name'])
            # Test policy without creating shared export files.
            req=urllib.request.Request(base+'/api/products',data=b'{}',headers={'Content-Type':'application/json','Origin':base.replace('http:','https:')},method='POST')
            with self.assertRaises(urllib.error.HTTPError) as same_origin: client.open(req)
            self.record('HTTPS same host reaches input validation','HTTPS Origin on tunnel host',400,same_origin.exception.code)
            req=urllib.request.Request(base+'/api/products',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://other.example'},method='POST')
            with self.assertRaises(urllib.error.HTTPError) as cross_origin: client.open(req)
            self.record('foreign origin blocked','Origin https://other.example',403,cross_origin.exception.code)
            with auth_request('/api/auth/logout',{}) as r: json.load(r)
            with self.assertRaises(urllib.error.HTTPError) as logged_out: client.open(base+'/api/products')
            self.record('logout revokes access','GET after logout',401,logged_out.exception.code)
            with self.assertRaises(urllib.error.HTTPError) as wrong:
                auth_request('/api/auth/login',dict(username='api_tester',password='wrong-password-123'))
            self.record('incorrect password rejected','synthetic incorrect password',401,wrong.exception.code)
            with auth_request('/api/auth/login',dict(username='api_tester',password='test-password-123')) as r:
                self.record('login existing account','correct synthetic credentials','api_tester',json.load(r)['user']['username'])
            req=urllib.request.Request(base+'/api/account/profile',data=json.dumps(dict(display_name='API profile',bio='Synthetic',avatar_color='green',user_id=999)).encode(),headers={'Content-Type':'application/json'},method='PUT')
            with client.open(req) as r:
                profile=json.load(r)['user']
                self.record('profile update uses session identity','payload tries user_id 999',['API profile','api_tester'],[profile['display_name'],profile['username']])
            req=urllib.request.Request(base+'/api/account/settings',data=json.dumps(dict(font_size='extra-large',default_filter='error')).encode(),headers={'Content-Type':'application/json'},method='PUT')
            with client.open(req) as r:
                self.record('account font setting persisted','PUT extra-large','extra-large',json.load(r)['user']['font_size'])
            with client.open(base+'/api/auth/me') as r:
                self.record('profile returned on next request','GET me','API profile',json.load(r)['user']['display_name'])
        finally: server.shutdown();server.server_close();thread.join()
        try:
            urllib.request.urlopen(base+'/api/health',timeout=1)
            actual=False
        except urllib.error.URLError: actual=True
        self.record('service unavailable','GET after server stopped',True,actual)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(QualityTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (Path(__file__).parent/'test_results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(not result.wasSuccessful())
