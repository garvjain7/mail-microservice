# =============================================================================
# mail_microservice/main.py
# =============================================================================
# This is the RECEIVER side of the V2 mail architecture.
# Deployed on Fly.io (SMTP ports open, free tier).
#
# Your main CodeAlive backend (Render) calls this service over HTTPS.
# This service then sends the actual email via smtplib → Gmail.
#
# SECURITY
# --------
# Every request must include the header:
#   x-api-key: <MAIL_SERVICE_API_KEY>
# Requests without a valid key get 401. This prevents anyone external
# from using your mail service to send arbitrary emails.
#
# ENVIRONMENT VARIABLES (set in Fly.io dashboard)
# ------------------------------------------------
#   MAIL_EMAIL            Gmail sender address
#   MAIL_PASSWORD         Gmail App Password (not your login password)
#   MAIL_SERVICE_API_KEY  shared secret — must match the one in your main backend
# =============================================================================

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

load_dotenv()

MAIL_EMAIL           = os.getenv("MAIL_EMAIL")
MAIL_PASSWORD        = os.getenv("MAIL_PASSWORD")
MAIL_SERVICE_API_KEY = os.getenv("MAIL_SERVICE_API_KEY")

app = FastAPI(docs_url=None, redoc_url=None)  # disable public docs in production


# ── Auth dependency ───────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)):
    """
    Validates the x-api-key header on every request.
    Rejects with 401 if missing or incorrect.
    This is the only gate between the internet and your mail sender.
    """
    if not MAIL_SERVICE_API_KEY:
        raise HTTPException(500, "Mail service API key not configured on server")
    if x_api_key != MAIL_SERVICE_API_KEY:
        raise HTTPException(401, "Invalid API key")


# ── SMTP sender ───────────────────────────────────────────────────────────────

def _send(to: str, subject: str, body: str) -> bool:
    """Internal. Sends email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"]    = f"CodeAlive <{MAIL_EMAIL}>"
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(MAIL_EMAIL, MAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[mail_microservice] Failed to send to {to}: {e}")
        return False


# ── Request models ────────────────────────────────────────────────────────────

class WaitlistPayload(BaseModel):
    to: str

class ResetPayload(BaseModel):
    to: str
    token: str

class VerifyPayload(BaseModel):
    to: str
    token: str

class WorkshopInvitePayload(BaseModel):
    to: str
    room_title: str
    room_url: str
    host_name: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"status": "running", "service": "codealive mail microservice"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/send/waitlist")
def send_waitlist(payload: WaitlistPayload, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)

    subject = "You're on the CodeAlive Waitlist! 🚀"
    body = f"""Hi there,

Thank you for joining the CodeAlive waitlist!

We're excited to have you. We'll notify you as soon as our real-time
collaborative coding rooms are ready for early access.

In the meantime, feel free to use our instant code sharing editor
at https://codealive.onrender.com/editor

Best,
The CodeAlive Team"""

    ok = _send(payload.to, subject, body)
    if not ok:
        raise HTTPException(500, "Failed to send email")
    return {"ok": True}


@app.post("/send/reset-password")
def send_reset(payload: ResetPayload, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)

    reset_link = f"https://codealive.onrender.com/reset-password?token={payload.token}"
    subject = "Reset your CodeAlive password 🔐"
    body = f"""Hi there,

We received a request to reset your password for your CodeAlive account.
Click the link below to set a new password:

{reset_link}

If you didn't request this, you can safely ignore this email.
The link will expire in 20 minutes.

Best,
The CodeAlive Team"""

    ok = _send(payload.to, subject, body)
    if not ok:
        raise HTTPException(500, "Failed to send email")
    return {"ok": True}


@app.post("/send/verify")
def send_verify(payload: VerifyPayload, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)

    verify_link = f"https://codealive.onrender.com/verify-email?token={payload.token}"
    subject = "Verify your CodeAlive email ✉️"
    body = f"""Hi there,

Please verify your email address by clicking the link below:

{verify_link}

The link will expire in 24 hours.

Best,
The CodeAlive Team"""

    ok = _send(payload.to, subject, body)
    if not ok:
        raise HTTPException(500, "Failed to send email")
    return {"ok": True}


@app.post("/send/workshop-invite")
def send_workshop_invite(payload: WorkshopInvitePayload, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)

    subject = f"Invitation to Workshop: {payload.room_title} 🚀"
    body = f"""Hi there,

{payload.host_name} has invited you to join a real-time collaborative coding workshop on CodeAlive.

Workshop Title: {payload.room_title}
Join here: {payload.room_url}

In this workshop, you'll be able to code together in real-time, share insights, and build together.

Note: You must be logged into your CodeAlive account to join.

Best,
The CodeAlive Team"""

    ok = _send(payload.to, subject, body)
    if not ok:
        raise HTTPException(500, "Failed to send email")
    return {"ok": True}
