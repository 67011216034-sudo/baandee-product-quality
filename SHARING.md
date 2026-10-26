# แชร์เดโมให้เปิดจากอินเทอร์เน็ต

## เวอร์ชัน Streamlit

เปิด Streamlit ด้วย `python -m streamlit run streamlit_app.py` แล้วรัน tunnel ชี้ไป `http://127.0.0.1:8501` แทน port 8765 ใช้ URL `https://....trycloudflare.com` ที่โปรแกรมสร้างในรอบนั้น เว็บนี้รัน Streamlit บนเครื่องและไม่ได้ deploy บน Streamlit Community Cloud

ถ้าตรวจ Origin ผ่าน proxy ให้กำหนด `--browser.serverAddress` เป็นชื่อโฮสต์ที่ tunnel สร้าง และ `--browser.serverPort 443` โดยยังเปิด XSRF/CORS protection อยู่ ไม่ควรปิด protections เพื่อให้เชื่อมต่อได้

## เว็บเดิม

`http://127.0.0.1:8765` เปิดได้เฉพาะเครื่องที่รันระบบ คนที่อยู่อีกเครื่องต้องใช้ลิงก์ HTTPS ที่สร้างผ่าน tunnel หรือ deploy ไปยังโฮสติ้งที่รองรับ Python และ storage ถาวร

## ลิงก์เดโมชั่วคราวผ่าน Cloudflare Tunnel

ดาวน์โหลด `cloudflared` จาก https://developers.cloudflare.com/tunnel/downloads/ และรันเซิร์ฟเวอร์ใน terminal แรก:

```powershell
python app.py
```

เปิด terminal ที่สองในโฟลเดอร์ที่มี cloudflared:

```powershell
.\cloudflared.exe tunnel --url http://127.0.0.1:8765 --protocol http2 --no-autoupdate
```

ส่ง URL `https://....trycloudflare.com` ที่โปรแกรมแสดงให้ผู้ทดลอง เปิดเครื่องและโปรแกรมทั้งสองค้างไว้ ลิงก์หยุดทำงานเมื่อปิด tunnel/ปิดเครื่อง และ URL เปลี่ยนเมื่อสร้างใหม่ ไม่มีการติดตั้งเป็น Windows service

ผู้ที่มี URL ต้องสมัครสมาชิกและเข้าสู่ระบบก่อนดู เพิ่ม และแก้ข้อมูลสังเคราะห์ร่วมกันในฐานข้อมูลเดียวกัน ระบบมีบัญชีผู้ใช้แล้ว แต่ยังไม่มีสิทธิ์ผู้อนุมัติหรือการแบ่งบทบาท ห้ามเพิ่มข้อมูลส่วนบุคคลหรือข้อมูลลับผ่านเดโม

Cloudflare ให้ Quick Tunnel สำหรับทดสอบและพัฒนา ไม่รับประกัน uptime จึงไม่ควรใช้ URL นี้เป็นลิงก์ถาวรในการส่งงานแทน GitHub repository

หากต้องการเปิดใช้งานได้แม้ปิดเครื่อง ต้องย้าย Python API และฐานข้อมูลไป hosting ที่รองรับ persistent disk หรือเปลี่ยนใช้ฐานข้อมูลที่โฮสต์แยกต่างหาก โดยเพิ่มการยืนยันตัวตนและสิทธิ์แก้ไขก่อนใช้งานจริง
