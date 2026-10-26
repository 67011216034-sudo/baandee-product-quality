"""BaanDee local product quality API. Python 3.10+, no third-party dependencies."""
import csv
import io
import json
import math
import os
import re
import sqlite3
import threading
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from auth import Auth, SESSION_SECONDS

ROOT = Path(__file__).resolve().parent
FIELDS = ('product_id', 'product_name', 'category', 'unit_price_thb')
LOCK = threading.RLock()

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, db=None):
        self.db = str(db or ROOT / 'data' / 'products.sqlite3')
        self.policy = json.loads((ROOT/'data/generated/quality_policy.json').read_text(encoding='utf-8'))
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, product_id TEXT, product_name TEXT, category TEXT,
                unit_price_thb TEXT, source TEXT, updated_at TEXT, revision INTEGER DEFAULT 1);
                CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, row_id INTEGER,
                action TEXT, before_json TEXT, after_json TEXT, reason TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);''')
            if not c.execute("SELECT 1 FROM metadata WHERE key='initialized'").fetchone():
                self._import(c, ROOT/'data/raw/products.csv', 'original')
                self._import(c, ROOT/'data/generated/demo_products.csv', 'synthetic-demo')
                c.execute("INSERT INTO metadata VALUES ('initialized', ?)", (now(),))

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def _import(self, c, path, source):
        with path.open(encoding='utf-8-sig', newline='') as source_file:
            for row in csv.DictReader(source_file):
                c.execute('INSERT INTO products(product_id,product_name,category,unit_price_thb,source,updated_at) VALUES (?,?,?,?,?,?)',
                          tuple(row[f] for f in FIELDS)+(source,now()))

    def rows(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM products ORDER BY id')]

    def inspect(self, row, counts):
        issues = []
        def add(code, severity, field, message, suggestion=None):
            issues.append(dict(code=code,severity=severity,field=field,message=message,suggestion=suggestion))
        pid = row['product_id'].strip()
        if not pid: add('MISSING_ID','error','product_id','ไม่มีรหัสสินค้า')
        elif counts[pid] > 1: add('DUPLICATE_ID','error','product_id','รหัสซ้ำ ต้องให้คนตรวจสอบ ห้ามรวมรายการอัตโนมัติ')
        if pid and not re.fullmatch(r'(?:SKU|DEMO)-[A-Z0-9]+(?:-[A-Z0-9]+)*',pid):
            add('ID_FORMAT','review','product_id','รูปแบบรหัสไม่ตรงกฎของต้นแบบ')
        for f in FIELDS:
            if row[f] != row[f].strip(): add('WHITESPACE','warning',f,'มีช่องว่างหัวหรือท้าย',row[f].strip())
        if not row['product_name'].strip(): add('MISSING_NAME','error','product_name','ไม่มีชื่อสินค้า ไม่สามารถเดาแทนได้')
        cat = row['category'].strip()
        if cat not in self.policy['categories']:
            match = self.policy['aliases'].get(cat.lower())
            if match: add('CATEGORY_ALIAS','warning','category','หมวดหมู่ต่างรูปแบบ แก้ได้ตามตารางเทียบ',match)
            else: add('UNKNOWN_CATEGORY','review','category','ไม่พบหมวดหมู่ในมาตรฐาน ต้องให้คนยืนยัน')
        try:
            price = float(row['unit_price_thb'])
            if not math.isfinite(price) or price <= 0: raise ValueError()
            if price > self.policy['price_review_above']:
                add('PRICE_REVIEW','review','unit_price_thb','ราคาเกินเกณฑ์ทบทวน ยังสรุปไม่ได้ว่าผิด')
        except (ValueError,TypeError): add('INVALID_PRICE','error','unit_price_thb','ราคาต้องเป็นตัวเลขที่มากกว่า 0')
        status = 'error' if any(i['severity']=='error' for i in issues) else 'review' if any(i['severity']=='review' for i in issues) else 'warning' if issues else 'pass'
        return dict(row, issues=issues, status=status)

    def report(self):
        rows = self.rows()
        counts = Counter(r['product_id'].strip() for r in rows)
        checked = [self.inspect(r,counts) for r in rows]
        return dict(products=checked,summary=dict(Counter(r['status'] for r in checked)),total=len(rows),checked_at=now(),policy=self.policy)

    def save(self, payload, row_id=None):
        if not isinstance(payload,dict): raise ValueError('ข้อมูลต้องเป็น object')
        if any(not isinstance(payload.get(f),str) or len(payload[f])>500 for f in FIELDS):
            raise ValueError('กรอกข้อมูลสินค้าเป็นข้อความ ความยาวไม่เกิน 500 ตัวอักษร')
        reason = payload.get('reason','')
        if not isinstance(reason,str) or not reason.strip() or len(reason)>1000:
            raise ValueError('ต้องระบุเหตุผลการเพิ่มหรือแก้ไข ไม่เกิน 1000 ตัวอักษร')
        # Invalid drafts may be saved, but remain quarantined by report/export.
        with LOCK, self.connect() as c:
            before = None
            if row_id is not None:
                old = c.execute('SELECT * FROM products WHERE id=?',(row_id,)).fetchone()
                if old is None: raise KeyError('ไม่พบสินค้า')
                before = dict(old)
                if payload.get('revision') != old['revision']: raise RuntimeError('ข้อมูลถูกแก้ไขแล้ว กรุณาโหลดใหม่')
                c.execute('UPDATE products SET product_id=?,product_name=?,category=?,unit_price_thb=?,updated_at=?,revision=revision+1 WHERE id=?',
                          tuple(payload[f] for f in FIELDS)+(now(),row_id))
            else:
                row_id = c.execute('INSERT INTO products(product_id,product_name,category,unit_price_thb,source,updated_at) VALUES (?,?,?,?,?,?)',
                                   tuple(payload[f] for f in FIELDS)+('user-created',now())).lastrowid
            after = dict(c.execute('SELECT * FROM products WHERE id=?',(row_id,)).fetchone())
            c.execute('INSERT INTO audit(row_id,action,before_json,after_json,reason,created_at) VALUES (?,?,?,?,?,?)',
                      (row_id,'update' if before else 'create',json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),reason.strip(),now()))
        return after

    def history(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC')]

    def normalize(self):
        changed=0
        with LOCK:
            for row in self.report()['products']:
                payload = {f:row[f].strip() for f in FIELDS}
                alias = self.policy['aliases'].get(payload['category'].lower())
                if alias: payload['category']=alias
                if any(payload[f]!=row[f] for f in FIELDS):
                    self.save(dict(payload, revision=row['revision'], reason='ปรับช่องว่างและหมวดหมู่ตามกฎ policy v'+self.policy['version']),row['id'])
                    changed+=1
        return dict(changed=changed)

    def export(self, folder=None):
        report=self.report()
        folder=Path(folder) if folder else ROOT/'data/cleaned'
        folder.mkdir(exist_ok=True)
        for name,selected in [('products_clean.csv',[r for r in report['products'] if r['status']=='pass']),('quarantine.csv',[r for r in report['products'] if r['status']!='pass'])]:
            with (folder/name).open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(FIELDS)+['source','status','issues'])
                writer.writeheader()
                for r in selected: writer.writerow({**{k:r[k] for k in FIELDS},'source':r['source'],'status':r['status'],'issues':'; '.join(i['code'] for i in r['issues'])})
        (folder/'quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (folder/'correction_log.json').write_text(json.dumps(self.history(),ensure_ascii=False,indent=2),encoding='utf-8')
        return dict(clean=sum(r['status']=='pass' for r in report['products']),quarantine=sum(r['status']!='pass' for r in report['products']))

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def send(self, status, obj, mime='application/json; charset=utf-8', headers=None):
        body = json.dumps(obj,ensure_ascii=False).encode() if mime.startswith('application/json') else obj
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('X-Frame-Options','DENY')
        for key, value in (headers or {}).items(): self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)
    def current_user(self):
        return self.server.auth.user(self.server.auth.token(self.headers.get('Cookie')))
    def cookie(self, token='', clear=False):
        host = self.headers.get('Host','').split(':')[0]
        secure = host not in {'localhost','127.0.0.1','[::1]'}
        return 'bd_session='+token+'; Path=/; HttpOnly; SameSite=Lax; Max-Age='+str(0 if clear else SESSION_SECONDS)+('; Secure' if secure else '')
    def do_GET(self):
        path=urlparse(self.path).path
        user = self.current_user()
        if path=='/api/auth/me': return self.send(200,{'user':user}) if user else self.send(401,{'error':'กรุณาเข้าสู่ระบบ'})
        if path.startswith('/api/') and path!='/api/health' and not user:
            return self.send(401,{'error':'กรุณาเข้าสู่ระบบก่อนใช้งาน'})
        if path=='/api/account/profile': return self.send(200,{'user':user})
        if path=='/api/products': return self.send(200,self.server.store.report())
        if path=='/api/history': return self.send(200,self.server.store.history())
        if path=='/api/health': return self.send(200,{'status':'ok'})
        if path=='/' and not user: return self.send(303,b'',mime='text/plain',headers={'Location':'/login'})
        if path in {'/login','/register'} and user: return self.send(303,b'',mime='text/plain',headers={'Location':'/'})
        files={'/':('index.html','text/html; charset=utf-8'),'/login':('auth.html','text/html; charset=utf-8'),'/register':('auth.html','text/html; charset=utf-8'),'/auth.js':('auth.js','text/javascript; charset=utf-8'),'/account.js':('account.js','text/javascript; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if path in files:
            name,mime=files[path]
            return self.send(200,(ROOT/'static'/name).read_bytes(),mime)
        return self.send(404,{'error':'ไม่พบข้อมูล'})
    def do_POST(self): self.mutate()
    def do_PUT(self): self.mutate()
    def mutate(self):
        origin=self.headers.get('Origin')
        # HTTPS may terminate at a tunnel before reaching the loopback HTTP server.
        # Keep the same-host restriction for both schemes; never allow other origins.
        host = self.headers.get('Host','')
        if origin and origin not in {'http://'+host, 'https://'+host}:
            return self.send(403,{'error':'ไม่อนุญาตคำขอจากเว็บไซต์อื่น'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>20000: raise ValueError('ข้อมูลใหญ่เกินกำหนด')
            payload=json.loads(self.rfile.read(length) or b'{}')
            path=urlparse(self.path).path
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                return self.send(415,{'error':'ต้องส่งข้อมูลเป็น JSON'})
            if self.command=='POST' and path in {'/api/auth/register','/api/auth/login'}:
                address = self.headers.get('CF-Connecting-IP',self.client_address[0])
                if not self.server.auth.check_rate(address):
                    return self.send(429,{'error':'ลองหลายครั้งเกินไป กรุณารอ 5 นาที'},headers={'Retry-After':'300'})
                user = self.server.auth.register(payload) if path.endswith('/register') else self.server.auth.login(payload)
                token = self.server.auth.session(user,self.server.auth.token(self.headers.get('Cookie')))
                return self.send(200,{'user':user},headers={'Set-Cookie':self.cookie(token)})
            if self.command=='POST' and path=='/api/auth/logout':
                self.server.auth.logout(self.server.auth.token(self.headers.get('Cookie')))
                return self.send(200,{'ok':True},headers={'Set-Cookie':self.cookie(clear=True)})
            user = self.current_user()
            if not user: return self.send(401,{'error':'กรุณาเข้าสู่ระบบก่อนใช้งาน'})
            if self.command=='PUT' and path=='/api/account/profile':
                return self.send(200,{'user':self.server.auth.update_profile(user['id'],payload)})
            if self.command=='PUT' and path=='/api/account/settings':
                return self.send(200,{'user':self.server.auth.update_settings(user['id'],payload)})
            if self.command=='POST' and path=='/api/account/password':
                if not self.server.auth.check_rate('password:'+str(user['id'])):
                    return self.send(429,{'error':'ลองหลายครั้งเกินไป กรุณารอ 5 นาที'})
                try:
                    self.server.auth.change_password(user['id'],payload,self.server.auth.token(self.headers.get('Cookie')))
                except PermissionError as e:
                    return self.send(403,{'error':str(e)})
                return self.send(200,{'ok':True})
            if self.command=='POST' and path=='/api/products': result=self.server.store.save(payload)
            elif self.command=='PUT' and re.fullmatch('/api/products/[0-9]+',path): result=self.server.store.save(payload,int(path.rsplit('/',1)[1]))
            elif self.command=='POST' and path=='/api/normalize': result=self.server.store.normalize()
            elif self.command=='POST' and path=='/api/export': result=self.server.store.export()
            else: return self.send(404,{'error':'ไม่พบ API'})
            self.send(200,result)
        except KeyError: self.send(404,{'error':'ไม่พบสินค้า'})
        except PermissionError as e: self.send(401,{'error':str(e)})
        except RuntimeError as e: self.send(409,{'error':str(e)})
        except (ValueError,TypeError) as e: self.send(400,{'error':str(e)})
        except sqlite3.Error: self.send(503,{'error':'ฐานข้อมูลไม่พร้อม กรุณาลองใหม่'})

def serve(port=8765,db=None):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.store=Store(db)
    server.auth=Auth(server.store)
    return server

if __name__=='__main__':
    server=serve(int(os.environ.get('BAANDEE_PORT','8765')))
    print('BaanDee Quality: http://127.0.0.1:'+str(server.server_port),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
