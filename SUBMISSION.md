# ชุดส่งงาน BaanDee Product Data Quality Checker

ตรวจชุดงานด้านเทคนิค: 26 ตุลาคม 2026 (Asia/Bangkok)

## ลิงก์ส่งอาจารย์

- Repository: https://github.com/67011216034-sudo/baandee-product-quality
- เว็บสาธิต: https://baandee-quality-studio.streamlit.app/
- Main file: `streamlit_app.py` / Python 3.12 / branch `main`
- เวอร์ชันสุดท้ายที่โจทย์กำหนด: Git tag หรือ GitHub release `v1.0-final` (ยังไม่สร้างระหว่างรอข้อมูลสมาชิกและการทบทวนจริงของทีม)

ส่ง Repository URL เป็นหลัก เว็บเป็นช่องทางสาธิตเพิ่มเติม ไม่ต้องส่งรายงานแยก เนื้อหาการส่งงานอยู่ใน repository นี้

## ตารางเทียบกับโจทย์

| ข้อกำหนด | หลักฐานใน repository | สถานะ |
|---|---|---|
| ปัญหา ผู้ใช้ คุณค่าที่คาดหวังและสมมติฐาน | `README.md` | มีเอกสาร |
| ข้อมูลเดิมอย่างน้อยหนึ่งแหล่ง | `data/raw/products.csv`, `PROVENANCE.json` | 82 แถว ตรวจ SHA-256 ตรงต้นฉบับ |
| แหล่งใหม่ที่บทบาทต่างจากเดิม | `data/generated/quality_policy.json` | ใช้ categories/aliases เชื่อมหมวดหมู่ และเกณฑ์ราคาส่งทบทวน |
| อธิบายข้อมูลที่สร้างเพิ่ม | `data/generated/demo_products.csv`, `README.md` | สังเคราะห์ 6 แถวเพื่อทดสอบ ไม่อ้างเป็นปัญหาที่พบในต้นฉบับ |
| ปัญหาข้อมูลอย่างน้อยสามประเภท | `app.py`, `pipeline_evidence.json` | ชื่อว่าง ราคาผิด รหัสซ้ำ หมวดหมู่ต่างรูปแบบ/กำกวม |
| วิธีตรวจ วิธีจัดการ ก่อน/หลัง และรายการให้คนตรวจ | `scripts/prepare_data.py`, `data/cleaned/` | ทำซ้ำแล้ว ผ่าน 73 -> 78 แถว; แยกตรวจ 10 แถว |
| เก็บ raw แยก clean | `data/raw/`, `data/cleaned/` | สคริปต์ยืนยัน checksum และไม่แก้ฐานข้อมูลหน้าเว็บ |
| ขอบเขตระหว่างระบบ | `streamlit_client.py` -> HTTP -> `app.py` | UI ส่ง REST request จริง ไม่ใช่เรียก validator โดยตรง |
| สร้าง บันทึก เรียกกลับ แก้ไข ผ่าน UI | `streamlit_app.py`, `tests/test_streamlit.py` | ผ่าน AppTest บนฐานข้อมูลชั่วคราว |
| บันทึกคงอยู่และตรวจซ้ำได้ | `tests/test_system.py` กรณี create/update/reopen | ผ่านบน SQLite local; Cloud มีข้อจำกัดตาม `DEPLOYMENT.md` |
| Success และกรณีส่งต่อให้มนุษย์ | alias ที่ยืนยันได้ เทียบกับ `Bed room` และรหัสซ้ำ | ระบบไม่เดาค่าที่ไม่มีหลักฐาน |
| ทดสอบอย่างน้อยห้ากรณีพร้อม input/expected/actual/pass-fail | `tests/test_results.json`, `tests/streamlit_test_results.json` | ผ่าน 24 test methods; JSON มีหลักฐาน 36 checks |
| API success/not found/unavailable | `tests/test_system.py`, `tests/test_streamlit.py` | ทดสอบแล้ว แม้หัวข้อสถานการณ์ API ในโจทย์ระบุ optional |
| วิธีติดตั้งและ dependencies | `README.md`, `requirements.txt`, `.env.example` | มีคำสั่งรันและตัวแปรที่ใช้ |
| เปิดเผยการใช้ AI และการตัดสินใจของคน | `AI_USE.md` | มี disclosure; รอสมาชิกเติมผลทบทวนของตนตามจริง |
| สมาชิก 3-4 คนและหลักฐานการแบ่งงาน | ตารางท้าย `README.md` และ `AI_USE.md` | รอชื่อ รหัส หน้าที่ ผลตรวจจริง; ไม่สร้างประวัติผลงานแทนทีม |
| Tag/release `v1.0-final` | Git tag / GitHub release | รอทีมทบทวนเวอร์ชันสุดท้าย |

## สิ่งที่ผู้จัดทำยังต้องทำจริงก่อนส่ง

- [ ] กรอกชื่อ รหัสนิสิต และหน้าที่จริงของสมาชิก 3-4 คนใน README
- [ ] สมาชิกทดลองส่วนของตนและกรอกผลตรวจ/การตัดสินใจจริงใน AI_USE.md
- [ ] ตรวจว่าทุกคนอธิบายแหล่งข้อมูล กฎ REST API และข้อจำกัดได้
- [ ] ซ้อมตาม `DEMO_GUIDE.md` จบภายใน 8 นาที แล้วเตรียมตอบ 4 นาที
- [ ] ทดสอบเปิด Repository URL และเว็บจากอีกเครื่อง/อีกเครือข่ายก่อนวันนำเสนอ
- [ ] หลังข้อมูลทีมครบและตรวจเวอร์ชันที่จะส่งแล้ว สร้างและ push `v1.0-final`
- [ ] ส่ง URL และนัดอาจารย์ตามช่องทางที่อาจารย์กำหนด

คำสั่ง tag หลังตรวจครบ (รันใน Git checkout ที่มีงานเวอร์ชันส่ง):

```powershell
git status --short
git tag -a v1.0-final -m "BaanDee final submission"
git push origin main
git push origin v1.0-final
```

ต้อง commit งานที่ตรวจแล้วก่อนสร้าง tag และอย่าทับ tag ที่เผยแพร่แล้วโดยไม่แจ้งทีม

## การตรวจสอบล่าสุดและขอบเขตหลักฐาน

ผลรันวันที่ 26 ตุลาคม 2026: system/API 10 tests, auth/account 9 tests, Streamlit AppTest 5 tests ผ่านทั้งหมด ดู `tests/verification_summary.json` ผล test เป็นการทดสอบ local และฐานข้อมูลชั่วคราว ไม่ใช่การยืนยันทุกฟังก์ชันบน Cloud

Cloud ตรวจพบหน้า login/register แล้ว บัญชี local ไม่ได้อัปโหลดขึ้น Cloud ต้องสมัครใหม่ ไฟล์ SQLite ของ Cloud ไม่รับประกันการคงอยู่หลัง reboot/redeploy ให้ดาวน์โหลด export และเตรียม local demo ไว้ การสาธิต local ทำได้โดยไม่พึ่ง Cloud เมื่อ dependencies ติดตั้งไว้แล้ว

ห้ามแนบฐานข้อมูลบัญชีจริง `.env`, secrets, token, log หรือ virtual environment ลง repository/ZIP ส่งงาน

## ข้อความพร้อมใช้ในช่องส่งงาน

ชื่อโครงงาน: BaanDee Product Data Quality Checker (ระบบตรวจคุณภาพข้อมูลสินค้า)

Repository URL: https://github.com/67011216034-sudo/baandee-product-quality

Demo URL: https://baandee-quality-studio.streamlit.app/

เวอร์ชันส่ง: ระบุ `v1.0-final` เมื่อสร้างและ push แล้วเท่านั้น

รายละเอียดติดตั้ง แหล่งข้อมูล กฎ หลักฐานก่อน/หลัง ผลทดสอบ และการใช้ AI อยู่ใน repository สมาชิกและวันนำเสนอให้เติมตามข้อมูลจริงก่อนส่ง

## นัดนำเสนอ

เอกสารโจทย์ระบุเริ่มนำเสนอ 19 ตุลาคม และภายใน 30 ตุลาคม ให้เสนอ 3 ตัวเลือกที่เป็นคนละวัน ถ้ายังไม่ได้นัด ใช้ข้อความนี้และเติมข้อมูลจริงก่อนส่งด้วยตนเอง:

> เรียนอาจารย์ กลุ่ม [ชื่อกลุ่ม/รายชื่อสมาชิก] ขออนุญาตนัดนำเสนอโครงงาน BaanDee Product Data Quality Checker โดยเสนอวันเวลาที่สมาชิกพร้อม 3 ตัวเลือกดังนี้
>
> 1. วันที่ [วัน/เดือน] เวลา [เวลา]
> 2. วันที่ [คนละวัน] เวลา [เวลา]
> 3. วันที่ [คนละวัน] เวลา [เวลา]
>
> Repository: https://github.com/67011216034-sudo/baandee-product-quality
>
> รบกวนอาจารย์แจ้งช่วงเวลาที่สะดวกครับ/ค่ะ

ข้อความนี้เป็นร่าง ยังไม่ได้ส่งให้อาจารย์และยังไม่ได้ยืนยันนัดหมาย
