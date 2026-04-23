import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import settings
from ldap3 import Server, Connection, ALL
from app.logging_config import logger
from app.security.rate_limit import InMemoryRateLimiter

router = APIRouter(prefix="/admin/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/api/auth/token")

login_rate_limiter = InMemoryRateLimiter(
    max_attempts=settings.auth_rate_limit_max_attempts,
    window_seconds=settings.auth_rate_limit_window_seconds,
    block_seconds=settings.auth_rate_limit_block_seconds,
)

class Token(BaseModel):
    access_token: str
    token_type: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"

def authenticate_ldap(username, password):
    user_dn = f"{username}@{settings.ldap_domain}"
    try:
        import ssl
        tls = getattr(ssl, "PROTOCOL_TLS", getattr(ssl, "PROTOCOL_TLSv1_2"))
        import ldap3

        # --- TLS hardening ---
        # Default: require TLS + certificate validation in production (DEBUG=False).
        require_tls = (
            settings.ldap_require_tls
            if settings.ldap_require_tls is not None
            else (not settings.debug)
        )

        validate_str = (settings.ldap_tls_validate or "").strip().upper()
        if validate_str == "CERT_NONE":
            validate_mode = ssl.CERT_NONE
        elif validate_str == "CERT_OPTIONAL":
            validate_mode = ssl.CERT_OPTIONAL
        elif validate_str == "CERT_REQUIRED":
            validate_mode = ssl.CERT_REQUIRED
        else:
            validate_mode = ssl.CERT_NONE if settings.debug else ssl.CERT_REQUIRED

        tls_config = ldap3.Tls(
            validate=validate_mode,
            version=tls,
            ca_certs_file=settings.ldap_tls_ca_cert_file,
        )
        
        # PHP Script checks if bind works, or uses StartTLS if error 8 occurs.
        # Initialize server with the TLS config (it won't use SSL initially since use_ssl=False)
        ldap_url = (settings.ldap_server or "").strip()
        use_ssl = False
        ldap_host = ldap_url
        if ldap_url.startswith("ldaps://"):
            use_ssl = True
            ldap_host = ldap_url[len("ldaps://") :]
        elif ldap_url.startswith("ldap://"):
            ldap_host = ldap_url[len("ldap://") :]
        ldap_host = ldap_host.rstrip("/")

        server = Server(
            ldap_host,
            use_ssl=use_ssl,
            get_info=ALL,
            tls=tls_config,
            connect_timeout=settings.ldap_timeout,
        )
        
        # Python ldap3 handles StartTLS natively. Setting auto_referrals=False matches LDAP_OPT_REFERRALS=0
        conn = Connection(
            server,
            user=user_dn,
            password=password,
            auto_referrals=False,
            receive_timeout=settings.ldap_timeout,
        )
        
        try:
            # Enforce StartTLS on ldap:// in production unless explicitly disabled.
            if require_tls and not use_ssl:
                if not conn.open():
                    return False
                if not conn.start_tls():
                    return False

            if not conn.bind():
                # ldap3 stores response details in conn.result. Error 8 is strongerAuthRequired.
                if (
                    (not use_ssl)
                    and conn.result
                    and (
                        conn.result.get("result") == 8
                        or "strongerAuthRequired" in str(conn.result.get("description", ""))
                    )
                ):
                    # Try StartTLS fallback
                    if not conn.start_tls():
                        return False
                    if not conn.bind():
                        return False
                else:
                    return False
                
            return True
        finally:
            try:
                conn.unbind()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"LDAP Error: {e}", exc_info=True)
        return False

@router.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    client_ip = get_client_ip(request)
    request_id = getattr(request.state, "request_id", None)

    # Rate limit (per IP and per username+IP)
    keys = [
        f"ip:{client_ip}",
        f"userip:{(form_data.username or '').lower()}:{client_ip}",
    ]
    for key in keys:
        blocked = await login_rate_limiter.check_blocked(key)
        if blocked.blocked:
            logger.warning(
                f"AUTH blocked username={form_data.username} ip={client_ip} retry_after={blocked.retry_after_seconds}s request_id={request_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(blocked.retry_after_seconds or 0)},
            )

    is_authenticated = False
    role = "teacher" # Default role
    
    # 1. Fallback / Local Admin check
    if form_data.username == settings.admin_username and verify_password(form_data.password, get_password_hash(settings.admin_password)):
        is_authenticated = True
        role = "admin"
    else:
        # 2. Check if username is allowed in LDAP admin list
        allowed_admins = [u.strip() for u in settings.admin_users_list.split(',')]
        
        # 3. Perform LDAP Auth for ANY user to allow them as teacher
        if authenticate_ldap(form_data.username, form_data.password):
            is_authenticated = True
            if form_data.username in allowed_admins:
                role = "admin"
                
    if not is_authenticated:
        # Register failures for rate limiting
        triggered_block = None
        for key in keys:
            status_obj = await login_rate_limiter.register_failure(key)
            if status_obj.blocked:
                triggered_block = status_obj

        if triggered_block and triggered_block.retry_after_seconds:
            logger.warning(
                f"AUTH rate_limited username={form_data.username} ip={client_ip} retry_after={triggered_block.retry_after_seconds}s request_id={request_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(triggered_block.retry_after_seconds)},
            )

        logger.warning(f"AUTH failed username={form_data.username} ip={client_ip} request_id={request_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Success: reset counters and audit log
    for key in keys:
        await login_rate_limiter.reset(key)
    logger.info(f"AUTH success username={form_data.username} role={role} ip={client_ip} request_id={request_id}")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        role: str = payload.get("role", "teacher")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return {"username": username, "role": role}

async def verify_admin_role(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required.",
        )
    return user["username"]
