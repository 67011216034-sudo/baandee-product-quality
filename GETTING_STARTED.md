# เปิดใช้งาน BaanDee Quality Studio

## เปิดผ่านเว็บ

เปิด https://baandee-quality-studio.streamlit.app/ หรือดับเบิลคลิก `open_online.url` ไม่ต้องติดตั้ง Python ผู้ใช้ใหม่กด “สมัครสมาชิก” ในหน้าแอป บัญชีของเว็บเป็นคนละชุดกับฐานข้อมูลบนเครื่อง

เว็บเป็นพื้นที่สาธิตข้อมูลสังเคราะห์และใช้สินค้าร่วมกัน SQLite บน Cloud ไม่รับประกันการคงอยู่หลัง reboot/redeploy ดู DEPLOYMENT.md

## เปิดบนเครื่อง Windows

1. แตก ZIP ทั้งหมดก่อน อย่าเปิดไฟล์ .bat จากข้างใน ZIP
2. เปิดโฟลเดอร์ `baandee-quality` แล้วดับเบิลคลิก **`start_streamlit.bat`**
3. ตัวเปิดใหม่ตรวจ Python ที่ใช้งานได้จริง ไม่ถือว่า Microsoft Store alias คือ Python ที่ติดตั้งแล้ว รองรับ Python 3.10 ขึ้นไป แนะนำ 3.12
4. ถ้ายังไม่มี dependencies ตัวเปิดจะสร้าง `.venv` ในโฟลเดอร์โครงการและติดตั้งจาก `requirements.txt` ครั้งแรกต้องต่ออินเทอร์เน็ต รอจนติดตั้งเสร็จ ไม่ต้องเปิดแบบ Administrator
5. เปิดหน้าแอปที่ `http://localhost:8501` หากเบราว์เซอร์ไม่เปิดให้อัตโนมัติ เก็บหน้าต่าง terminal ไว้ระหว่างใช้งาน กด Ctrl+C เพื่อหยุด

### หากขึ้น No working Python / Python was not found

เครื่องยังไม่มี Python ที่ตัวเปิดใช้งานได้ ให้ติดตั้ง Python 3.12 จาก https://www.python.org/downloads/windows/ โดยเลือก **Add python.exe to PATH** แล้วเปิด `start_streamlit.bat` ใหม่ ไม่ต้องปิดระบบความปลอดภัย Windows และไม่ต้องแก้ App execution aliases

ถ้าต้องการใช้ทันที ให้ใช้ลิงก์เว็บด้านบนแทนการรัน local

### หากติดตั้งไลบรารีไม่สำเร็จ

ตรวจอินเทอร์เน็ตและพื้นที่ว่าง แล้วเปิด `start_streamlit.bat` ใหม่ หากเครือข่ายแจ้งปัญหา certificate ให้ใช้เครือข่าย/ใบรับรองที่ถูกต้อง ห้ามปิดการตรวจ TLS เพื่อข้ามปัญหา

ติดตั้งและรันเองได้จาก terminal ในโฟลเดอร์โครงการ:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

เรียก Python ใน `.venv` โดยตรง ไม่จำเป็นต้อง activate จึงไม่ต้องเปลี่ยน PowerShell execution policy

### หาก port 8501 ถูกใช้อยู่

ปิดแอป BaanDee เก่าที่ตนเองเปิดไว้ หรือใช้ port อื่น:

```powershell
.\start_streamlit.bat --port 8502
```

อย่าปิด process ของผู้อื่น ตัวเปิดใหม่ไม่หยุดหรือฆ่าโปรแกรมที่ใช้งานอยู่

## ตรวจความพร้อมโดยยังไม่เปิดแอป

```powershell
.\start_streamlit.bat --check
```

แสดง Python และสถานะ dependencies โดยไม่ติดตั้ง ไม่เริ่ม server และไม่เปิดเบราว์เซอร์ ถ้า `setup_needed` เป็น true ให้เปิดไฟล์ตามปกติเพื่อติดตั้ง

`python launch.py --setup-only` ใช้เตรียม dependencies ล่วงหน้าได้ ส่วน `start.bat` เปิดเว็บ HTML/API รุ่นเดิม ไม่ใช่หน้าจอ Streamlit

## ข้อมูลและการส่งงาน

ข้อมูล local อยู่ `data/products.sqlite3` อย่าลบหากต้องการเก็บบัญชีและรายการเดิม หลังปิดเปิดแอปใช้ไฟล์เดิมได้ ฐานข้อมูล `.venv` และรหัสลับไม่รวมใน ZIP/Git

อ่าน `SUBMISSION.md` สำหรับรายการส่ง และ `DEMO_GUIDE.md` สำหรับบทสาธิต สมาชิกทั้งสี่มีชื่อใน README แล้ว ผลทบทวนรายบุคคลให้กรอกตามที่ทดลองจริง
