"""ESPReL LDAP gateway — API สำหรับระบบ NRED (FastAPI) บน intranet มหาวิทยาลัยนเรศวร

หน้าที่เดียว: รับชื่อผู้ใช้/รหัสผ่านจากแอป ESPReL MRA (Vercel) → bind LDAP/AD แบบเดียวกับ NRED (user@nu.local)
→ ตอบ "ผ่าน/ไม่ผ่าน" (+ ชื่อ อีเมล หน่วยงาน ถ้าอ่านได้)  ไม่เก็บรหัสผ่าน ไม่ออก token ไม่ต่อฐานข้อมูล

ความปลอดภัย
  - HTTPS เท่านั้น (ตรวจ X-Forwarded-Proto จาก reverse proxy) — ปิดได้เฉพาะตอนทดสอบด้วย ESPREL_ALLOW_HTTP=1
  - ทุกคำขอต้องลงลายเซ็น HMAC-SHA256 ด้วยคีย์ลับร่วม (ไม่ส่งคีย์ไปกับคำขอ):
        X-ESPReL-Timestamp: เวลา unix (คลาดได้ไม่เกิน 60 วินาที)
        X-ESPReL-Nonce:     ค่าสุ่มใช้ครั้งเดียว (กันการส่งซ้ำ / replay)
        X-ESPReL-Signature: hex(HMAC(key, "v1\\n{timestamp}\\n{nonce}\\n{sha256(body)}"))
  - คำตอบลงลายเซ็นกลับ ผูกกับ nonce ของคำขอ → แอป ESPReL เชื่อเฉพาะคำตอบจาก gateway ตัวจริง
        X-ESPReL-Signature: hex(HMAC(key, "v1-resp\\n{nonce}\\n{status}\\n{sha256(body)}"))
  - ปฏิเสธรหัสผ่านว่างเสมอ (AD บางเครื่องถือว่า anonymous bind "ผ่าน"), ชื่อผู้ใช้ต้องเป็น [a-z0-9._-]
  - จำกัดการลองผิด: 8 ครั้ง/15 นาที ต่อชื่อผู้ใช้ และ 30 ครั้ง/15 นาที ต่อ IP · จำกัดขนาดคำขอ 2 KB
  - ข้อความตอบกลับไม่บอกเหตุผลละเอียด · log ไม่มีรหัสผ่าน · คีย์ต้องยาวอย่างน้อย 32 ตัวอักษร ไม่งั้นปิดบริการ
  - จำกัด IP ผู้เรียกได้ด้วย ESPREL_ALLOWED_IPS (ถ้า proxy ส่ง X-Forwarded-For มาให้ ระบุ ESPREL_TRUST_PROXY=1)

ติดตั้งใน NRED: คัดลอกไฟล์นี้เป็น app/routers/esprel_gateway.py แล้วใน main.py
        from app.routers.esprel_gateway import router as esprel_gateway_router
        app.include_router(esprel_gateway_router)
    (หรือรัน install_into_nred.py ในโฟลเดอร์โปรเจค NRED)
รันแยกได้: uvicorn esprel_ldap_gateway:app --host 127.0.0.1 --port 8701

ตั้งค่าใน .env ของ NRED (ไฟล์นี้อ่าน .env เองด้วย เพราะ pydantic Settings ไม่ส่งค่าเข้า os.environ)
  ESPREL_GATEWAY_KEY=<คีย์ลับยาว ≥32 ตัว — ค่าเดียวกับ LDAP_GATEWAY_KEY ของแอป ESPReL>
  ESPREL_LDAP_SERVER=ldap://10.10.10.71   ESPREL_LDAP_DOMAIN=nu.local   (ค่าเริ่มต้นเหมือน NRED)
  ESPREL_LDAP_BASE_DN=DC=nu,DC=local      (ไม่บังคับ — ใช้ดึงชื่อ/อีเมล/หน่วยงาน)
  ESPREL_LDAP_REQUIRE_TLS=0|1  ESPREL_LDAP_TLS_VALIDATE=0|1  ESPREL_LDAP_CA_CERT_FILE=  ESPREL_LDAP_TIMEOUT=8
  ESPREL_ALLOWED_IPS=  ESPREL_TRUST_PROXY=1  ESPREL_ALLOW_HTTP=0
"""
import hashlib
import hmac
import json
import logging
import os
import re
import ssl
import threading
import time

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response

log = logging.getLogger("esprel_gateway")
PROTOCOL = "v1"
MAX_SKEW = 60            # วินาที
MAX_BODY = 2048          # bytes
USER_RE = re.compile(r"[a-z0-9._\-]{1,64}")


def _load_env_file():
    """อ่าน .env (ของ NRED) เฉพาะค่าที่ขึ้นต้นด้วย ESPREL_ ถ้ายังไม่มีใน environment"""
    path = os.environ.get("ESPREL_ENV_FILE", ".env")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("ESPREL_") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


_load_env_file()


def _env(k, d=None):
    v = os.environ.get(k)
    return v if v not in (None, "") else d


class Settings:
    def __init__(self):
        self.key = (_env("ESPREL_GATEWAY_KEY") or "").encode()
        self.ldap_server = _env("ESPREL_LDAP_SERVER", "ldap://10.10.10.71")
        self.ldap_domain = _env("ESPREL_LDAP_DOMAIN", "nu.local")
        self.base_dn = _env("ESPREL_LDAP_BASE_DN", "")
        self.require_tls = _env("ESPREL_LDAP_REQUIRE_TLS", "0") == "1"
        self.tls_validate = _env("ESPREL_LDAP_TLS_VALIDATE", "1") == "1"
        self.ca_file = _env("ESPREL_LDAP_CA_CERT_FILE")
        self.timeout = int(_env("ESPREL_LDAP_TIMEOUT", "8"))
        self.allowed_ips = {x.strip() for x in (_env("ESPREL_ALLOWED_IPS", "") or "").split(",") if x.strip()}
        self.trust_proxy = _env("ESPREL_TRUST_PROXY", "1") == "1"
        self.allow_http = _env("ESPREL_ALLOW_HTTP", "0") == "1"

    @property
    def key_ok(self):
        return len(self.key) >= 32


S = Settings()


# ----------------------------------------------------------------- ลายเซ็น
def body_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sign_request(key: bytes, ts: str, nonce: str, body: bytes) -> str:
    return hmac.new(key, f"{PROTOCOL}\n{ts}\n{nonce}\n{body_hash(body)}".encode(), hashlib.sha256).hexdigest()


def sign_response(key: bytes, nonce: str, status: int, body: bytes) -> str:
    return hmac.new(key, f"{PROTOCOL}-resp\n{nonce}\n{status}\n{body_hash(body)}".encode(), hashlib.sha256).hexdigest()


# ----------------------------------------------------------------- กันส่งซ้ำ + จำกัดการลองผิด (ในหน่วยความจำ)
class _Window:
    def __init__(self, limit, seconds):
        self.limit, self.seconds, self.hits, self.lock = limit, seconds, {}, threading.Lock()

    def _clean(self, k, now):
        self.hits[k] = [t for t in self.hits.get(k, []) if now - t < self.seconds]

    def blocked(self, k):
        now = time.time()
        with self.lock:
            self._clean(k, now)
            return len(self.hits[k]) >= self.limit

    def add(self, k):
        with self.lock:
            self.hits.setdefault(k, []).append(time.time())
            if len(self.hits) > 50000:          # กันหน่วยความจำโต
                self.hits.clear()


_user_fails = _Window(8, 900)
_ip_fails = _Window(30, 900)
_nonces, _nonce_lock = {}, threading.Lock()


def _nonce_fresh(nonce):
    now = time.time()
    with _nonce_lock:
        for n, t in list(_nonces.items()):
            if now - t > MAX_SKEW * 2:
                del _nonces[n]
        if nonce in _nonces:
            return False
        _nonces[nonce] = now
        return True


# ----------------------------------------------------------------- LDAP (แบบเดียวกับ NRED)
def _first(entry, attr):
    try:
        v = {k.lower(): x for k, x in entry.entry_raw_attributes.items()}.get(attr.lower())
    except Exception:  # noqa: BLE001
        return None
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if isinstance(v, bytes):
        v = v.decode("utf-8", "ignore")
    return str(v) if v else None


def ldap_bind(username: str, password: str):
    """(True/False, ข้อมูลผู้ใช้) — ยก RuntimeError เมื่อเชื่อมต่อ LDAP ไม่ได้"""
    from ldap3 import SIMPLE, Connection, Server, Tls
    from ldap3.core.exceptions import LDAPBindError, LDAPException
    from ldap3.utils.conv import escape_filter_chars

    use_ssl = S.ldap_server.lower().startswith("ldaps://")
    tls = Tls(validate=ssl.CERT_REQUIRED if S.tls_validate else ssl.CERT_NONE, ca_certs_file=S.ca_file or None)
    server = Server(S.ldap_server, use_ssl=use_ssl, tls=tls, connect_timeout=S.timeout)
    upn = f"{username}@{S.ldap_domain}"

    def connect():
        return Connection(server, user=upn, password=password, authentication=SIMPLE, receive_timeout=S.timeout,
                          check_names=False, raise_exceptions=False)
    try:
        conn = connect()
        if not use_ssl and S.require_tls:
            conn.open()
            conn.start_tls()
        if not conn.bind():
            if not use_ssl and not S.require_tls and (conn.result or {}).get("result") == 8:  # strongerAuthRequired
                conn = connect()
                conn.open()
                conn.start_tls()
                if not conn.bind():
                    return False, {}
            else:
                return False, {}
        info = {}
        if S.base_dn:
            try:
                conn.search(S.base_dn, f"(sAMAccountName={escape_filter_chars(username)})",
                            attributes=["displayName", "mail", "department"], size_limit=1)
                if conn.entries:
                    e = conn.entries[0]
                    info = {"full_name": _first(e, "displayName"), "email": _first(e, "mail"),
                            "department": _first(e, "department")}
            except LDAPException:
                pass
        conn.unbind()
        return True, info
    except LDAPBindError:
        return False, {}
    except LDAPException as ex:
        raise RuntimeError(type(ex).__name__) from ex


# ----------------------------------------------------------------- API
router = APIRouter(prefix="/api/esprel", tags=["esprel"], include_in_schema=False)


def _client_ip(request: Request):
    if S.trust_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def _reply(status: int, payload: dict, nonce: str = ""):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if nonce and S.key_ok:
        headers["X-ESPReL-Signature"] = sign_response(S.key, nonce, status, body)
    return Response(content=body, status_code=status, media_type="application/json", headers=headers)


@router.post("/ldap-verify")
async def ldap_verify(request: Request):
    ip = _client_ip(request)
    if not S.key_ok:
        log.error("ESPReL gateway disabled: ESPREL_GATEWAY_KEY missing or shorter than 32 chars")
        return _reply(503, {"ok": False, "error": "unavailable"})
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
    if proto != "https" and not S.allow_http:
        return _reply(400, {"ok": False, "error": "https required"})
    if S.allowed_ips and ip not in S.allowed_ips:
        return _reply(403, {"ok": False, "error": "forbidden"})
    if _ip_fails.blocked(ip):
        return _reply(429, {"ok": False, "error": "too many attempts"})

    ts = request.headers.get("x-esprel-timestamp", "")
    nonce = request.headers.get("x-esprel-nonce", "")
    sig = request.headers.get("x-esprel-signature", "")
    body = await request.body()
    if len(body) > MAX_BODY or not re.fullmatch(r"[A-Za-z0-9_\-]{16,64}", nonce or "") or not ts.isdigit():
        _ip_fails.add(ip)
        return _reply(403, {"ok": False, "error": "forbidden"})
    if abs(time.time() - int(ts)) > MAX_SKEW or not hmac.compare_digest(sig, sign_request(S.key, ts, nonce, body)):
        _ip_fails.add(ip)
        log.warning("ESPReL gateway: bad signature/timestamp from %s", ip)
        return _reply(403, {"ok": False, "error": "forbidden"})
    if not _nonce_fresh(nonce):
        _ip_fails.add(ip)
        return _reply(403, {"ok": False, "error": "replay"}, nonce)

    try:
        data = json.loads(body)
        user = str(data.get("username", "")).strip().lower()
        password = str(data.get("password", ""))
    except (ValueError, AttributeError):
        return _reply(400, {"ok": False, "error": "bad request"}, nonce)
    if not USER_RE.fullmatch(user) or not password or len(password) > 256:
        return _reply(401, {"ok": False}, nonce)
    if _user_fails.blocked(user):
        return _reply(429, {"ok": False, "error": "too many attempts"}, nonce)
    try:
        ok, info = ldap_bind(user, password)
    except RuntimeError as ex:
        log.error("ESPReL gateway: LDAP unavailable (%s)", ex)
        return _reply(502, {"ok": False, "error": "ldap unavailable"}, nonce)
    if not ok:
        _user_fails.add(user)
        _ip_fails.add(ip)
        log.info("ESPReL AUTH fail user=%s ip=%s", user, ip)
        return _reply(401, {"ok": False}, nonce)
    log.info("ESPReL AUTH ok user=%s ip=%s", user, ip)
    return _reply(200, {"ok": True, "username": user, **{k: v for k, v in info.items() if v}}, nonce)


@router.get("/ldap-health")
def ldap_health():
    # ไม่เปิดเผย IP/ค่าภายใน — บอกแค่ว่าพร้อมใช้งานหรือไม่
    return {"ok": S.key_ok, "protocol": PROTOCOL}


# รันแยกเป็นบริการเล็ก ๆ: uvicorn esprel_ldap_gateway:app --host 127.0.0.1 --port 8701
app = FastAPI(title="ESPReL LDAP gateway", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(router)
