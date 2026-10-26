"""Native Streamlit UI; all business reads and writes cross the REST boundary."""
import csv
import html
import io
import json
import os
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
from streamlit_client import ApiClient, ApiError

ROOT = Path(__file__).resolve().parent
LABELS = {'all': 'ทุกสถานะ', 'pass': 'ผ่านการตรวจ', 'error': 'ข้อมูลผิด', 'review': 'รอตรวจสอบ', 'warning': 'ปรับรูปแบบได้'}
SOURCES = {'all': 'ทุกแหล่งข้อมูล', 'original': 'ต้นฉบับ BaanDee', 'synthetic-demo': 'ชุดสาธิตสังเคราะห์', 'user-created': 'เพิ่มผ่านระบบ'}
AVATARS = {'purple': 'ม่วง', 'blue': 'ฟ้า', 'green': 'เขียว', 'rose': 'ชมพู'}
PAGES = ['คุณภาพข้อมูลสินค้า', 'เพิ่มสินค้า', 'ประวัติการแก้ไข', 'กฎและแหล่งข้อมูล', 'โปรไฟล์ของฉัน', 'ตั้งค่าบัญชี']

st.set_page_config(page_title='BaanDee • Quality Studio', page_icon='🏡', layout='wide', initial_sidebar_state='expanded')


@st.cache_resource
def api_endpoint():
    configured = os.environ.get('BAANDEE_API_URL', '').strip()
    if configured:
        if urlparse(configured).scheme not in {'http', 'https'}:
            raise ValueError('BAANDEE_API_URL ต้องเป็น http หรือ https')
        return configured
    from app import serve
    server = serve(0, os.environ.get('BAANDEE_DB_PATH') or None)
    threading.Thread(target=server.serve_forever, daemon=True, name='baandee-rest-api').start()
    return 'http://127.0.0.1:' + str(server.server_port)


def client():
    if 'api_client' not in st.session_state:
        # Cloudflare provides the actual visitor address; local/AppTest falls back
        # to an opaque per-session key. Credentials/tokens remain session-local.
        visitor = st.context.headers.get('CF-Connecting-IP') if st.context.headers else None
        st.session_state.api_client = ApiClient(api_endpoint(), visitor)
    return st.session_state.api_client


def call(path, method='GET', payload=None):
    return client().call(path, method, payload)


def flash(message):
    st.session_state.notice = message


def rerun():
    st.rerun()


def styling(user=None):
    size = {'normal': 16, 'large': 18, 'extra-large': 20}.get((user or {}).get('font_size'), 18)
    st.markdown('''<style>
    .stApp {background:#f8f7fc;color:#39334f}
    [data-testid="stSidebar"] {background:#20223c}
    [data-testid="stSidebar"] * {color:#eeeaf9}
    [data-testid="stSidebar"] [data-baseweb="select"] * {color:#3b3451}
    .block-container {padding-top:2.5rem;max-width:1450px}
    h1,h2,h3 {color:#463760!important;letter-spacing:-.4px}
    [data-testid="stMetric"] {background:white;border:1px solid #e7e2f2;border-radius:15px;padding:20px}
    [data-testid="stForm"] {background:#fff;border:1px solid #e5dff0;border-radius:15px;padding:24px}
    .stButton button,.stDownloadButton button {min-height:46px;border-radius:9px}
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {background:#7660d7;border-color:#7660d7}
    .hero {padding:25px 30px;background:#eee9fb;border:1px solid #dfd6f3;border-radius:16px;margin:10px 0 24px}
    .hero h2{margin:0 0 10px}.hero p{margin:0;color:#817193}
    .profile-avatar{display:flex;align-items:center;justify-content:center;width:88px;height:88px;border-radius:25px;background:#e8dffa;color:#7350a6;font-size:32px;margin:12px 0}
    [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {min-height:46px}
    @media(max-width:750px){
      .st-key-quality_metrics [data-testid="stHorizontalBlock"] {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
      .st-key-quality_metrics [data-testid="stColumn"] {width:100%!important;min-width:0!important}
      .st-key-quality_metrics [data-testid="stColumn"]:first-child {grid-column:span 2}
      .st-key-auth_intro h1 {display:none}
      .st-key-auth_intro [data-testid="stAlert"],.st-key-auth_intro [data-testid="stCaptionContainer"] {display:none}
    }
    </style>''', unsafe_allow_html=True)
    # Only a validated numeric preference enters CSS; never interpolate user text.
    st.markdown(f'''<style>
    .stMarkdown p,.stMarkdown li,[data-testid="stWidgetLabel"] p,
    [data-testid="stFormSubmitButton"] p,.stButton p,.stDownloadButton p,
    [data-testid="stRadio"] label p {{font-size:{size}px!important;line-height:1.75}}
    input,textarea,[data-baseweb="select"] {{font-size:{size}px!important}}
    [data-testid="stCaptionContainer"] p {{font-size:{max(14,size-3)}px!important;line-height:1.8}}
    h1{{font-size:{size+16}px!important}}h2{{font-size:{size+9}px!important}}h3{{font-size:{size+4}px!important}}
    </style>''', unsafe_allow_html=True)


def auth_page():
    styling()
    if st.session_state.get('notice'): st.info(st.session_state.pop('notice'))
    left, right = st.columns([1, 1.1], gap='large')
    with left:
        with st.container(key='auth_intro'):
            st.markdown('### baandee · Quality Studio')
            st.title('ข้อมูลที่พร้อมใช้\nเริ่มต้นที่นี่')
            st.write('ตรวจคุณภาพ จัดการสินค้า และติดตามทุกการเปลี่ยนแปลงในพื้นที่ทำงานเดียว')
            st.info('พื้นที่สาธิตสำหรับข้อมูลสังเคราะห์ สมาชิกทุกคนใช้ข้อมูลสินค้าชุดเดียวกัน')
            st.caption('ย้ายหน้าจอมาเป็น Streamlit · ใช้กฎและฐานข้อมูลเดิมผ่าน REST API')
    with right:
        mode = st.radio('บัญชีผู้ใช้', ['เข้าสู่ระบบ', 'สมัครสมาชิก'], horizontal=True, key='auth_mode')
        registering = mode == 'สมัครสมาชิก'
        st.subheader(mode)
        with st.form('register_form' if registering else 'login_form'):
            username = st.text_input('ชื่อผู้ใช้', max_chars=32, key='auth_username')
            st.caption('ใช้ a-z, 0-9 หรือ _ จำนวน 3–32 ตัว ไม่ต้องใช้อีเมลจริง')
            password = st.text_input('รหัสผ่าน', type='password', max_chars=128, key='auth_password')
            st.caption('รหัสผ่าน 10–128 ตัวอักษร')
            confirm = st.text_input('ยืนยันรหัสผ่าน', type='password', max_chars=128, key='auth_confirm') if registering else ''
            submitted = st.form_submit_button('สร้างบัญชีและเริ่มใช้งาน' if registering else 'เข้าสู่ระบบ', type='primary', width='stretch')
        if submitted:
            try:
                payload = dict(username=username, password=password)
                if registering: payload['confirm_password'] = confirm
                result = call('/api/auth/register' if registering else '/api/auth/login', 'POST', payload)
                st.session_state.user = result['user']
                st.session_state.status_filter = result['user']['default_filter']
                st.session_state.pop('auth_password', None)
                st.session_state.pop('auth_confirm', None)
                rerun()
            except ApiError as error:
                st.error(str(error))
        st.caption('ยังไม่มีบัญชี? เลือก “สมัครสมาชิก” ด้านบน · สมัครแล้วเข้าสู่ระบบได้ทันที')


def product_form(row=None):
    suffix = str(row['id']) if row else 'new'
    with st.form('product_' + suffix, clear_on_submit=row is None):
        first, second = st.columns(2)
        with first:
            product_id = st.text_input('รหัสสินค้า', value=row['product_id'] if row else '', max_chars=500)
            category = st.text_input('หมวดหมู่', value=row['category'] if row else '', max_chars=500)
        with second:
            product_name = st.text_input('ชื่อสินค้า', value=row['product_name'] if row else '', max_chars=500)
            price = st.text_input('ราคา (บาท)', value=row['unit_price_thb'] if row else '', max_chars=500)
        reason = st.text_area('เหตุผลการเพิ่มหรือแก้ไข', max_chars=1000)
        st.caption('บันทึกฉบับร่างที่ยังผิดได้ ระบบจะตรวจซ้ำและแยกจากข้อมูลที่ผ่านเสมอ')
        submitted = st.form_submit_button('บันทึกและตรวจใหม่' if row else 'เพิ่มสินค้า', type='primary')
    if submitted:
        payload = dict(product_id=product_id, product_name=product_name, category=category, unit_price_thb=price, reason=reason)
        if row: payload['revision'] = row['revision']
        try:
            saved = call('/api/products' + ('/' + str(row['id']) if row else ''), 'PUT' if row else 'POST', payload)
            st.session_state.pop('editing_snapshot', None)
            st.session_state.pop('export_zip', None)
            flash(f"บันทึก {saved['product_id'] or '(ไม่มีรหัส)'} สำเร็จ และเรียกกลับจากฐานข้อมูลแล้ว")
            rerun()
        except ApiError as error:
            st.error(str(error))
            if error.status == 409:
                st.warning('รายการถูกแก้ไขจากอุปกรณ์อื่น กด “ตรวจใหม่” เพื่อโหลดข้อมูลล่าสุดก่อนแก้ไข')


def csv_bytes(rows):
    output = io.StringIO(newline='')
    fields = ['product_id', 'product_name', 'category', 'unit_price_thb', 'source', 'status', 'issues']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({**{f: row[f] for f in fields if f != 'issues'}, 'issues': '; '.join(i['code'] for i in row['issues'])})
    return output.getvalue().encode('utf-8-sig')


def exports(report):
    clean = [row for row in report['products'] if row['status'] == 'pass']
    quarantine = [row for row in report['products'] if row['status'] != 'pass']
    a, b = st.columns(2)
    a.download_button('ดาวน์โหลดข้อมูลที่ผ่าน CSV', csv_bytes(clean), 'products_clean.csv', 'text/csv')
    b.download_button('ดาวน์โหลดรายการรอตรวจ CSV', csv_bytes(quarantine), 'quarantine.csv', 'text/csv')
    if st.button('สร้างชุดส่งออกพร้อมรายงานและประวัติ'):
        try:
            counts = call('/api/export', 'POST', {})
            history = call('/api/history')
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('products_clean.csv', csv_bytes(clean))
                archive.writestr('quarantine.csv', csv_bytes(quarantine))
                archive.writestr('quality_report.json', json.dumps(report, ensure_ascii=False, indent=2))
                archive.writestr('correction_log.json', json.dumps(history, ensure_ascii=False, indent=2))
            st.session_state.export_zip = output.getvalue()
            st.success(f"บันทึกผลฝั่ง API แล้ว: ผ่าน {counts['clean']} รายการ / แยกตรวจ {counts['quarantine']} รายการ")
        except ApiError as error:
            st.error(str(error))
    if st.session_state.get('export_zip'):
        st.download_button('ดาวน์โหลดชุดผลตรวจ ZIP', st.session_state.export_zip, 'baandee-quality-results.zip', 'application/zip')


def products_page():
    st.title('คุณภาพข้อมูลสินค้า')
    report = call('/api/products')
    passed = report['summary'].get('pass', 0)
    percent = round(100 * passed / report['total']) if report['total'] else 0
    st.markdown(f'<div class="hero"><h2>ข้อมูลพร้อมใช้ {percent}%</h2><p>ผ่านการตรวจ {passed} จาก {report["total"]} รายการ · ใช้กฎที่อธิบายได้</p></div>', unsafe_allow_html=True)
    with st.container(key='quality_metrics'):
        metrics = st.columns(5)
        for column, (label, value) in zip(metrics, [('สินค้าทั้งหมด', report['total'])] + [(LABELS[s], report['summary'].get(s, 0)) for s in ['pass', 'error', 'review', 'warning']]):
            column.metric(label, value)
    st.caption('ข้อมูลเริ่มต้น: ต้นฉบับ 82 รายการ + ชุดสาธิตสังเคราะห์ 6 รายการ ข้อมูลที่เพิ่มผ่านระบบจะแสดงแหล่งที่มาแยกกัน')
    one, two = st.columns(2)
    if one.button('ตรวจใหม่', width='stretch'):
        st.session_state.pop('editing_snapshot', None)
        rerun()
    if two.button('ปรับรูปแบบที่ยืนยันได้', width='stretch'):
        result = call('/api/normalize', 'POST', {})
        st.session_state.pop('editing_snapshot', None)
        st.session_state.pop('export_zip', None)
        flash(f"ปรับรูปแบบ {result['changed']} รายการแล้ว รายการกำกวมยังรอตรวจสอบ")
        rerun()
    search = st.text_input('ค้นหาสินค้า', placeholder='รหัส ชื่อ หรือหมวดหมู่')
    col1, col2 = st.columns(2)
    status = col1.selectbox('สถานะ', list(LABELS), format_func=LABELS.get, key='status_filter')
    source = col2.selectbox('แหล่งข้อมูล', list(SOURCES), format_func=SOURCES.get)
    rows = [r for r in report['products'] if (status == 'all' or r['status'] == status) and (source == 'all' or r['source'] == source) and any(search.lower() in r[f].lower() for f in ['product_id', 'product_name', 'category'])]
    table = [{'รหัสสินค้า': r['product_id'], 'ชื่อสินค้า': r['product_name'], 'หมวดหมู่': r['category'], 'ราคา': r['unit_price_thb'], 'ผลตรวจ': LABELS[r['status']], 'ปัญหาที่พบ': ' / '.join(i['message'] for i in r['issues']), 'แหล่งข้อมูล': SOURCES[r['source']]} for r in rows]
    st.dataframe(table, width='stretch', hide_index=True)
    st.caption(f"แสดง {len(rows)} จาก {report['total']} รายการ · ตรวจล่าสุด {report['checked_at']} · ต้นทางไม่ระบุเวลาอัปเดตสินค้า")
    if rows:
        st.subheader('ตรวจหลักฐานและแก้ไขสินค้า')
        lookup = {r['id']: r for r in rows}
        selected = st.selectbox('เลือกสินค้าที่ต้องการตรวจ', list(lookup), format_func=lambda key: f"{lookup[key]['product_id'] or '(ไม่มีรหัส)'} · {lookup[key]['product_name'] or '(ไม่มีชื่อ)'} · แถว {key}")
        if st.session_state.get('editing_snapshot', {}).get('id') != selected:
            st.session_state.editing_snapshot = lookup[selected].copy()
        row = st.session_state.editing_snapshot
        if row['issues']:
            for issue in row['issues']:
                message = issue['code'] + ' · ' + issue['message']
                if issue['suggestion'] is not None: message += ' → แนะนำ ' + str(issue['suggestion'])
                (st.error if issue['severity'] == 'error' else st.warning)(message)
        else:
            st.success('รายการนี้ผ่านทุกกฎ')
        st.caption(f"แหล่ง {SOURCES[row['source']]} · แก้ไขในระบบล่าสุด {row['updated_at']} · revision {row['revision']}")
        product_form(row)
    st.subheader('ส่งออกผลตรวจ')
    exports(report)


def history_page():
    st.title('ประวัติการแก้ไข')
    st.write('ตรวจสอบค่าเดิม ค่าใหม่ และเหตุผลของแต่ละรายการ')
    history = call('/api/history')
    if not history: st.info('ยังไม่มีการแก้ไขข้อมูล')
    for item in history:
        after = json.loads(item['after_json'])
        with st.expander(f"{after['product_id']} · {item['action']} · {item['created_at']}"):
            st.write('เหตุผล: ' + item['reason'])
            first, second = st.columns(2)
            first.write('ก่อนแก้ไข')
            first.json(json.loads(item['before_json']))
            second.write('หลังแก้ไข')
            second.json(after)


def rules_page():
    st.title('กฎและแหล่งข้อมูล')
    report = call('/api/products')
    st.subheader('ข้อมูลต้นฉบับ')
    st.write('products.csv จากชุด BaanDee จำนวน 82 รายการ เก็บต้นฉบับแยกจากข้อมูลทำงาน ไม่มีเวลาอัปเดตที่ต้นทางระบุ')
    st.subheader('แหล่งใหม่: นโยบายคุณภาพข้อมูล')
    st.write('quality_policy.json เป็นกฎสมมติที่ทีมออกแบบ เชื่อมหมวดหมู่กับ categories/aliases และเทียบราคากับเกณฑ์ส่งทบทวน')
    st.json(report['policy'])
    st.subheader('ข้อมูลสังเคราะห์สำหรับทดสอบ')
    st.write('demo_products.csv มี 6 รายการ รหัส DEMO-* ใช้สาธิตชื่อว่าง ราคาผิด รหัสซ้ำ หมวดหมู่ไม่รู้จัก และราคาที่ต้องทบทวน')
    st.warning('แก้ได้เฉพาะ alias และช่องว่างที่มีกฎยืนยัน ไม่เดาชื่อ ราคา หรือความหมายของ Bed room')
    st.code('Streamlit → urllib REST client → Python HTTP API → SQLite\nGET /api/products · POST /api/products · PUT /api/products/{id}')


def profile_page(user):
    st.title('โปรไฟล์ของฉัน')
    name = user['display_name'] or user['username']
    colors = {'purple': ('#e8dffa', '#7350a6'), 'blue': ('#e1edfb', '#456ba7'), 'green': ('#e1f3e9', '#377759'), 'rose': ('#f7e1ec', '#a45b7d')}
    background, foreground = colors.get(user['avatar_color'], colors['purple'])
    st.markdown(f'<div class="profile-avatar" style="background:{background};color:{foreground}">{html.escape(name[:2].upper())}</div>', unsafe_allow_html=True)
    st.subheader(name)
    st.caption('@' + user['username'] + ' · เข้าร่วม ' + datetime.fromtimestamp(user['created_at']).strftime('%Y-%m-%d'))
    with st.form('profile_form'):
        st.text_input('ชื่อผู้ใช้', value=user['username'], disabled=True)
        display = st.text_input('ชื่อที่แสดง', value=name, max_chars=60)
        bio = st.text_area('แนะนำตัวสั้น ๆ', value=user['bio'], max_chars=200)
        color = st.selectbox('สีโปรไฟล์', list(AVATARS), index=list(AVATARS).index(user['avatar_color']), format_func=AVATARS.get)
        saved = st.form_submit_button('บันทึกโปรไฟล์', type='primary')
    if saved:
        call('/api/account/profile', 'PUT', dict(display_name=display, bio=bio, avatar_color=color))
        flash('บันทึกโปรไฟล์แล้ว')
        rerun()
    st.info('โปรไฟล์เป็นของแต่ละบัญชี ส่วนข้อมูลสินค้าเป็นพื้นที่ทำงานร่วมกัน')


def settings_page(user):
    st.title('ตั้งค่าบัญชี')
    sizes = {'normal': 'มาตรฐาน', 'large': 'ใหญ่', 'extra-large': 'ใหญ่มาก'}
    with st.form('settings_form'):
        st.subheader('การแสดงผล')
        size = st.radio('ขนาดตัวอักษร', list(sizes), index=list(sizes).index(user['font_size']), format_func=sizes.get, horizontal=True)
        default = st.selectbox('ตัวกรองสินค้าเริ่มต้น', list(LABELS), index=list(LABELS).index(user['default_filter']), format_func=LABELS.get)
        saved = st.form_submit_button('บันทึกการตั้งค่า', type='primary')
    if saved:
        call('/api/account/settings', 'PUT', dict(font_size=size, default_filter=default))
        st.session_state.status_filter = default
        flash('บันทึกการตั้งค่าแล้ว')
        rerun()
    with st.form('password_form', clear_on_submit=True):
        st.subheader('เปลี่ยนรหัสผ่าน')
        current = st.text_input('รหัสผ่านปัจจุบัน', type='password', max_chars=128)
        new = st.text_input('รหัสผ่านใหม่', type='password', max_chars=128)
        confirm = st.text_input('ยืนยันรหัสผ่านใหม่', type='password', max_chars=128)
        st.caption('รหัสใหม่ 10–128 ตัวอักษร หลังเปลี่ยน อุปกรณ์อื่นต้องเข้าสู่ระบบใหม่')
        changed = st.form_submit_button('เปลี่ยนรหัสผ่าน')
    if changed:
        call('/api/account/password', 'POST', dict(current_password=current, new_password=new, confirm_password=confirm))
        flash('เปลี่ยนรหัสผ่านแล้ว อุปกรณ์อื่นต้องเข้าสู่ระบบใหม่')
        rerun()


def logout():
    call('/api/auth/logout', 'POST', {})
    st.session_state.clear()
    rerun()


def main():
    if 'user' not in st.session_state:
        auth_page()
        return
    try:
        user = call('/api/auth/me')['user']
        st.session_state.user = user
        styling(user)
        with st.sidebar:
            st.markdown('## baandee')
            st.caption('QUALITY STUDIO · STREAMLIT')
            st.write(user['display_name'] or user['username'])
            st.caption('@' + user['username'])
            page = st.radio('เมนูหลัก', PAGES, key='navigation')
            st.divider()
            st.caption('สมาชิก BaanDee Living · ข้อมูลสังเคราะห์')
            if st.button('ออกจากระบบ', width='stretch'): logout()
        if st.session_state.get('notice'): st.success(st.session_state.pop('notice'))
        if page == PAGES[0]: products_page()
        elif page == PAGES[1]:
            st.title('เพิ่มสินค้าใหม่')
            product_form()
        elif page == PAGES[2]: history_page()
        elif page == PAGES[3]: rules_page()
        elif page == PAGES[4]: profile_page(user)
        elif page == PAGES[5]: settings_page(user)
        st.divider()
        st.caption('BaanDee Quality Studio · Streamlit + REST API + SQLite · session หมดเมื่อรีเฟรชหน้าเบราว์เซอร์หรือครบ 12 ชั่วโมง')
    except ApiError as error:
        if error.status == 401:
            st.session_state.clear()
            flash('กรุณาเข้าสู่ระบบอีกครั้ง')
            rerun()
        st.error(str(error))
        if st.button('ลองเชื่อมต่ออีกครั้ง'): rerun()


main()
