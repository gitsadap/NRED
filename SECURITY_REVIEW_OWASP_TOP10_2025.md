# Security Review (OWASP Top 10:2025) – AGI Project

วันที่: 2026-04-22 (Asia/Bangkok)

## สถานะหลังแก้ไข (Patch ใน repo นี้)

- ✅ ลบ endpoint อัปโหลด CV แบบ public (`POST /api/faculty/upload-cv`) และเปลี่ยน `/teacher-portal` ให้ redirect ไป `/admin/login`
- ✅ ปรับ JWT/session timeout default เป็น 60 นาที + frontend auto-logout เมื่อ token หมดอายุ
- ✅ เพิ่ม rate limit สำหรับ `POST /admin/api/auth/token` + audit log (success/fail/blocked)
- ✅ ปรับ CORS ให้ตั้งค่าได้ผ่าน env และเพิ่ม security headers + CSP (ยกเว้นหน้า `/api/docs`/`/api/redoc`)
- ✅ Harden LDAP: ใน production บังคับ StartTLS (ldap://) และ validate certificate ตามค่าคอนฟิก
- ✅ ลดความเสี่ยง `pickle.load()` ใน chatbot: ใช้ `vector_meta.json` + `vector_db.npy` เป็นหลัก และมีสคริปต์ migrate

## 1) ภาพรวมโปรเจค (สรุปจากโค้ดใน repo นี้)

โปรเจคนี้เป็นเว็บแอป/เว็บ API ด้วย **FastAPI** มีทั้งหน้าเว็บ (Jinja2 templates) และ API JSON ใช้ฐานข้อมูล **PostgreSQL (asyncpg + SQLAlchemy AsyncSession)** และมีส่วน **Admin/Teacher CMS** ที่ล็อกอินด้วย **JWT (Bearer token)** ผ่าน LDAP หรือ local admin override

โครงสร้างสำคัญ:

- `main.py`  
  - สร้าง FastAPI app, เปิด CORS, mount static dirs (`/assets`, `/uploads`, `/static`, `/docs`) และ include routers
- `app/config.py`  
  - ค่าคอนฟิกทั้งหมด (DB, keys, JWT, LDAP, ฯลฯ) โหลดจาก `.env`
- `app/database.py`  
  - สร้าง async engine + session สำหรับ Postgres/Supabase (ปรับ statement cache ให้เข้ากับ PgBouncer)
- `app/routers/auth.py`  
  - endpoint ออก JWT: `POST /admin/api/auth/token`  
  - รองรับ LDAP bind และ local admin (username/password จาก env)
- `app/routers/admin.py`  
  - หน้าเว็บ admin: `/admin/`, `/admin/login`  
  - API สำหรับ CMS + อัปโหลดไฟล์ + แก้ CV (RBAC: `admin` vs `teacher`)
- `app/routers/public.py`  
  - หน้าเว็บ public (home/about/news/etc) + catch-all `/{slug}`  
  - มี endpoint อัปโหลด CV แบบ public ที่ควรระวัง (ดูหัวข้อ A01)
- `app/routers/api.py`  
  - Public API `/api/v1/*` (home/news/activities/faculty/research/coop-stats/ฯลฯ)
- `app/routers/chatbot.py`  
  - Chatbot endpoint `/api/v1/chatbot` ใช้ embeddings + Gemini และโหลดเวกเตอร์จากไฟล์ `.pkl` (ดูหัวข้อ A08)

## 2) Session / Login timeout (JWT)

### ปัจจุบันระบบใช้ “JWT เป็น session”

- หลังล็อกอิน: frontend เก็บ token ไว้ใน `localStorage` ชื่อ `admin_token`
- ทุก request ไป `admin` API จะใส่ header: `Authorization: Bearer <token>`
- ฝั่ง backend ตรวจ token จาก `exp` claim (วันหมดอายุ)

### การกำหนดเวลา session หมดอายุ

ตั้งค่าที่:

- `.env`: `ACCESS_TOKEN_EXPIRE_MINUTES` (นาที)
- `app/config.py`: `access_token_expire_minutes`
- `app/routers/auth.py`: นำค่าไปสร้าง `exp` ใน JWT

**ค่าเริ่มต้นถูกปรับเป็น 60 นาที** (แนะนำให้ override ใน production ตามนโยบายของหน่วยงาน)

### การบังคับ logout เมื่อ token หมดอายุ (กัน redirect loop)

ปรับปรุง frontend แล้ว:

- ถ้า token หมดอายุ/ไม่ถูกต้อง: จะลบ token แล้วส่งไปหน้า `/admin/login`
- ตั้ง timer ให้ auto logout เมื่อถึง `exp`
- หน้า `/admin/login` จะไม่ redirect กลับ `/admin/` ถ้า token หมดอายุ (ป้องกัน loop)

ไฟล์ที่เกี่ยวข้อง:

- `public/assets/js/admin.js`
- `templates/admin/login.html`

## 3) OWASP Top 10 (เวอร์ชันล่าสุด: 2025)

> หมายเหตุ: รายการที่คุณให้มาเป็นชุดคำของ OWASP Top 10:2021 หลายหัวข้อยังอยู่ แต่มีการ “ย้าย/เปลี่ยนชื่อ/รวม” ในปี 2025

Mapping แบบย่อ (2021 -> 2025):

- Broken Access Control -> **A01:2025 Broken Access Control**
- Security Misconfiguration -> **A02:2025 Security Misconfiguration**
- Vulnerable & Outdated Components -> **A03:2025 Software Supply Chain Failures** (ขยายขอบเขต)
- Cryptographic Failures -> **A04:2025 Cryptographic Failures**
- Injection -> **A05:2025 Injection**
- Insecure Design -> **A06:2025 Insecure Design**
- Identification & Authentication Failures -> **A07:2025 Authentication Failures** (เปลี่ยนชื่อ)
- Software & Data Integrity Failures -> **A08:2025 Software or Data Integrity Failures**
- Security Logging & Monitoring Failures -> **A09:2025 Security Logging and Alerting Failures** (เปลี่ยนชื่อ)
- SSRF -> **ถูกรวมอยู่ใน A01:2025 Broken Access Control**
- (ใหม่ใน 2025) -> **A10:2025 Mishandling of Exceptional Conditions**

---

## 4) ประเมินตาม OWASP Top 10:2025 (เฉพาะสิ่งที่เห็นจาก repo นี้)

ด้านล่างเป็น “จุดเสี่ยงที่เจอ/ควรตรวจต่อ” + แนวทางแก้แบบ actionable

### A01:2025 Broken Access Control (รวม SSRF)

สิ่งที่พบ/เสี่ยง:

- `POST /api/faculty/upload-cv` ใน `app/routers/public.py` **ไม่มี auth** และรับ `user_id` จากผู้ใช้โดยตรง  
  - ความเสี่ยง: ใครก็อัปโหลด/แทนที่ CV ของคนอื่นได้ (IDOR + Unauthorized file upload)
- การ map “ผู้ใช้ใน token -> Faculty record” ใน `app/routers/admin.py` มี fallback แบบ fuzzy (`ilike("%{username}%")`)  
  - ความเสี่ยง: ถ้า username ไป match อีเมลคนอื่นแบบบังเอิญ อาจแก้ไขข้อมูลผิดบัญชีได้

แนวทางแก้ (แนะนำเรียงลำดับ):

1) ปิด/ย้าย endpoint upload CV แบบ public ให้ใช้เฉพาะ flow ที่มี JWT (`/admin/*`) หรือทำ signed upload token เฉพาะกิจ  
2) ทำ object-level authorization ให้ชัดเจน (mapping table ระหว่าง `username` กับ `faculty_id`) และหลีกเลี่ยง fuzzy match
3) ทำ rate limit สำหรับ endpoint ที่กระทบข้อมูล (upload/submit)

### A02:2025 Security Misconfiguration

สิ่งที่พบ/เสี่ยง:

- CORS ใน `main.py` ตั้ง `allow_origins=["*"]` และ `allow_credentials=True` (ควรกำหนด allowlist origin ให้ชัด)
- มี default secret/admin credential ใน `app/config.py` (ต้องบังคับ override ใน production)
- บาง endpoint คืน error เป็น `str(e)` หรือแสดง traceback (information disclosure)

แนวทางแก้:

- ใช้ `ALLOW_ORIGINS` allowlist ตามโดเมนจริง, ปิด credentials ถ้าไม่จำเป็น
- บังคับตั้งค่า `SECRET_KEY`, `ADMIN_PASSWORD` (เช่น fail fast ถ้าเป็นค่า default)
- ปิด debug/SQL echo ใน production และทำ error response แบบไม่เปิดเผยรายละเอียด

### A03:2025 Software Supply Chain Failures

สิ่งที่พบ/เสี่ยง:

- `requirements.txt` ไม่ pin version (เสี่ยง dependency drift / CVE โผล่แบบไม่รู้ตัว)
- frontend โหลด JS/CSS จาก CDN โดยไม่มี SRI (เช่น Tailwind/TinyMCE/SweetAlert)

แนวทางแก้:

- pin dependency versions (เช่น `pip-compile`/Poetry) + ทำ dependency scanning (เช่น `pip-audit`)
- พิจารณา self-host critical JS/CSS หรือใส่ SRI + lock version

### A04:2025 Cryptographic Failures

สิ่งที่พบ/เสี่ยง:

- LDAP ตั้ง `CERT_NONE` (ไม่ verify cert) ใน `app/routers/auth.py`  
  - ความเสี่ยง: ถูก MITM ได้ในเครือข่ายที่ไม่ trusted
- JWT ใช้ HS256 ได้ แต่ต้องมั่นใจว่า `SECRET_KEY` แข็งแรงและไม่รั่ว

แนวทางแก้:

- เปิดการ verify certificate สำหรับ LDAP/StartTLS (ใช้ CA ที่เชื่อถือได้ หรือ pin cert)
- rotate secret/keys, แยก secret ต่อ environment, และเก็บใน secret manager

### A05:2025 Injection

สิ่งที่พบ/เสี่ยง:

- ใช้ SQLAlchemy เป็นหลัก (ดี) และ raw SQL ใน `app/routers/api.py` เป็น query คงที่ (ความเสี่ยง SQLi ต่ำ)
- ความเสี่ยงหลักจะไปอยู่ที่ **HTML content** ที่ admin ใส่ลง DB แล้วถูก render ออกสาธารณะ (stored XSS by design)  
  - ถ้า admin account ถูกยึด จะฝัง script ได้

แนวทางแก้:

- จำกัด/ sanitize HTML สำหรับ content ที่ต้องแสดงสาธารณะ (ถ้ารับได้ทาง UX)
- ทำ CSP (Content-Security-Policy) เพื่อ reduce impact ของ XSS

### A06:2025 Insecure Design

สิ่งที่พบ/เสี่ยง:

- ออกแบบ auth เป็น JWT + localStorage (กัน CSRF ได้ แต่เพิ่มแรงกระแทกเมื่อเกิด XSS)
- ไม่มี refresh token / rotation / revocation flow
- บาง flow (เช่น upload CV แบบ public) บ่งชี้ว่ามี design ที่ยังไม่ “secure-by-default”

แนวทางแก้:

- ย้าย token ไป HttpOnly cookie + เพิ่ม CSRF protection หรือทำ BFF pattern
- ออกแบบ refresh token (short-lived access token + rotating refresh token)
- threat model สำหรับ admin/teacher journey และ file upload journey

### A07:2025 Authentication Failures

สิ่งที่พบ/เสี่ยง:

- `POST /admin/api/auth/token` ไม่มี rate limit / lockout (เสี่ยง brute force)
- local admin override (username/password) ถ้าเผลอใช้ค่า default จะเสี่ยงมาก

แนวทางแก้:

- เพิ่ม rate limit ต่อ IP/username + lockout ตามนโยบาย
- บังคับเปลี่ยน admin password, พิจารณา MFA สำหรับ admin

### A08:2025 Software or Data Integrity Failures

สิ่งที่พบ/เสี่ยง:

- `app/routers/chatbot.py` ใช้ `pickle.load()` โหลดไฟล์เวกเตอร์ (`*.pkl`)  
  - ความเสี่ยง: ถ้าไฟล์ถูกแก้ไข/ถูกแทนที่ → RCE ได้ทันที

แนวทางแก้:

- เปลี่ยน format ไปเป็นที่ปลอดภัยกว่า (เช่น JSON/NPY/Parquet/SQLite) และตรวจ hash/signature ก่อนโหลด
- จำกัด permission ของโฟลเดอร์ที่เก็บ artifacts และปิดช่องทางอัปโหลด/แก้ไฟล์เหล่านี้จากภายนอก

### A09:2025 Security Logging and Alerting Failures

สิ่งที่พบ/เสี่ยง:

- log ส่วนใหญ่เป็น app log ทั่วไป ยังไม่ใช่ audit log (login success/fail, admin actions, file upload/delete)
- ไม่มี alerting เมื่อมีเหตุการณ์ผิดปกติ

แนวทางแก้:

- เพิ่ม audit log สำหรับ auth + admin operations (รวม user/role/ip/user-agent/request-id)
- ทำ alert rule (เช่น login fail หลายครั้ง, upload แปลก, delete จำนวนมาก)

### A10:2025 Mishandling of Exceptional Conditions

สิ่งที่พบ/เสี่ยง:

- มีบางจุดที่คืน error detail/traceback กลับ client (info leakage)
- บางจุด catch exception แล้ว fallback แบบ “เงียบ” อาจทำให้ระบบ fail-open หรือยากต่อการสืบสวน

แนวทางแก้:

- ทำ error handling แบบมาตรฐาน: แยกข้อความสำหรับผู้ใช้ vs รายละเอียดใน log
- เพิ่ม request-id correlation และปรับระดับ log ตาม severity

---

## 5) สรุปงานที่ควรทำต่อ (Priority)

P0 (ควรแก้ทันที):

- ปิด/ป้องกัน endpoint upload CV แบบ public (`/api/faculty/upload-cv`)
- บังคับ override ค่า `SECRET_KEY` และ admin credential
- เพิ่ม rate limit ที่ `/admin/api/auth/token`
- เลิกใช้ `pickle.load()` หรือ verify integrity ก่อนโหลด

P1:

- จำกัด CORS allowlist
- เพิ่ม audit logging + alerting
- วางแผน token storage แบบปลอดภัยกว่า localStorage (HttpOnly cookie / BFF)
