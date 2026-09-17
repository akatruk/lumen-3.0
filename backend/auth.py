import hashlib
import hmac
import secrets
import time
from fastapi import HTTPException, Request
from .db import connect
from .config import settings

def allowed_google_email(email):
    return email.strip().lower() in {e.strip().lower() for e in settings.google_allowed_emails.split(',') if e.strip()}


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
    return salt+':'+digest

def verify(password, stored):
    return hmac.compare_digest(hash_password(password,stored.split(':')[0]),stored)

def current_user(request: Request):
    token = request.cookies.get('lumen_session','')
    with connect() as db:
        user = db.execute('SELECT users.id,users.email,sessions.auth_method FROM sessions JOIN users ON users.id=sessions.user_id WHERE token=? AND expires>?',
                          (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    if not user: raise HTTPException(401,'unauthorized')
    if settings.google_sso_only and (user['auth_method'] != 'google' or not allowed_google_email(user['email'])):
        raise HTTPException(401,'unauthorized')
    return {'id': user['id'], 'email': user['email']}
