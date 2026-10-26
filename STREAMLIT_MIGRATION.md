# ย้ายหน้าจอมาเป็น Streamlit

## สิ่งที่ย้ายแล้ว

หน้าจอหลักเป็น `streamlit_app.py` ใช้ Streamlit widgets และ forms จริง ได้แก่ login/register, รายการและสรุปคุณภาพสินค้า, เพิ่มสินค้า, แก้ข้อมูลพร้อมเหตุผลและ revision, ประวัติ, กฎ, โปรไฟล์, การตั้งค่า, เปลี่ยนรหัสผ่าน และการดาวน์โหลดผลตรวจ CSV/ZIP

`streamlit_client.py` ส่ง HTTP request ไป REST API จริง ขอบเขตระหว่างระบบยังอยู่ครบตามโจทย์ ส่วน `app.py` และ `auth.py` ใช้ business logic/ฐานข้อมูลเดิม หน้าจอเดิมใน static/ ยังเก็บไว้ ไม่ได้ลบหรือแทนที่ข้อมูลต้นฉบับ

API ภายในใช้ port ว่างบน 127.0.0.1 เปิดเพียงครั้งเดียวผ่าน `st.cache_resource` เฉพาะ resource นี้แชร์ต่อ process ส่วน ApiClient และ cookie jar เก็บใน `st.session_state` แยกต่อ session ไม่ cache ข้อมูลผู้ใช้ทั้งระบบ

## วิธีเริ่ม

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

เปิด http://localhost:8501 หรือใช้ start_streamlit.bat บัญชีในเว็บเก่าใช้ได้ถ้าเป็น SQLite ไฟล์เดิม รหัสผ่านยังเป็น hash เดิม ไม่มีการคัดลอกรหัสผ่านข้อความปกติ

## วิธีทดสอบ

```powershell
python tests/test_system.py
python tests/test_auth.py
python tests/test_streamlit.py
```

AppTest สร้างฐานข้อมูลชั่วคราวของตัวเอง ตรวจ native widgets จริงและส่ง REST request จริง ครอบคลุมสมัคร/ล็อกอิน/ออกจากระบบ เพิ่มและแก้สินค้า ประวัติ โปรไฟล์ การตั้งค่า แยก session ล็อกอินผิด ไม่พบ API และบริการไม่พร้อม ผล input/expected/actual/pass-fail อยู่ tests/streamlit_test_results.json

## บัญชี Streamlit กับบัญชี BaanDee

ผู้ใช้แอปสมัครบัญชี BaanDee ในฟอร์มของแอปได้ ไม่ต้องสมัคร Streamlit เพื่อเปิดเว็บหรือรัน local

บัญชีบน Streamlit Community Cloud ใช้สำหรับผู้ดูแลที่จะ deploy แอปเท่านั้น หากจะ deploy ต้องมี repository ที่บัญชีนั้นเข้าถึงได้ และเลือก main file เป็น `streamlit_app.py` ในโฟลเดอร์โครงการ พร้อม requirements.txt และ .streamlit/config.toml

อัปโหลด GitHub แล้วที่ https://github.com/67011216034-sudo/baandee-product-quality (main) และยืนยันหน้าแอปบน Community Cloud แล้วที่ https://baandee-quality-studio.streamlit.app/ การเตรียมไฟล์และการแชร์ tunnel ไม่ใช่การ deploy ขึ้น Community Cloud

## ข้อจำกัดการเก็บข้อมูล

บนเครื่องนี้ SQLite อยู่บนดิสก์และคงข้อมูลหลังปิดเปิดโปรแกรม ส่วนบนบริการ cloud ห้ามถือว่าไฟล์ SQLite ใน runtime จะคงอยู่ตลอดการ reboot/redeploy ต้องจัด storage ถาวรหรือโฮสต์ backend แยกก่อนใช้เป็นแหล่งข้อมูลระยะยาว ตัวแปร BAANDEE_API_URL รองรับการชี้ไป backend แยก แต่ยังต้อง deploy และตรวจการเข้าถึง endpoint นั้นจริง

Streamlit session เริ่มใหม่เมื่อรีเฟรชหน้า/เปิดแท็บใหม่ จึงอาจต้องล็อกอินอีกครั้ง แม้บัญชีและข้อมูลในฐานข้อมูลยังอยู่ การแชร์ tunnel ยังต้องเปิดเครื่องและโปรแกรมค้างไว้
