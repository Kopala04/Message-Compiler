from __future__ import annotations

import imaplib
import email
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message as EmailMessage
from typing import Tuple


@dataclass
class ImapAccountConfig:
    host: str
    email: str
    password: str
    mailbox: str = "INBOX"
    ssl: bool = True


def _decode_mime_header(value: str | None) -> str | None:
    if not value:
        return value
    parts = decode_header(value)
    decoded = []
    for text, enc in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _decode_part_payload(part: EmailMessage) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _extract_text_and_html(msg: EmailMessage) -> Tuple[str | None, str | None]:
    text = None
    html = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue

            if ctype == "text/plain" and text is None:
                text = _decode_part_payload(part).strip()
            elif ctype == "text/html" and html is None:
                html = _decode_part_payload(part).strip()

            if text and html:
                break
    else:
        ctype = (msg.get_content_type() or "").lower()
        if ctype == "text/html":
            html = _decode_part_payload(msg).strip()
        else:
            text = _decode_part_payload(msg).strip()

    return text, html


def _connect(cfg: ImapAccountConfig):
    if cfg.ssl:
        return imaplib.IMAP4_SSL(cfg.host)
    return imaplib.IMAP4(cfg.host)


def fetch_latest_headers(cfg: ImapAccountConfig, limit: int = 30) -> list[dict]:
    """
    UID-based header fetch. provider_msg_id will be UID (string of digits).
    """
    imap = _connect(cfg)
    imap.login(cfg.email, cfg.password)
    imap.select(cfg.mailbox)

    status, data = imap.uid("search", None, "ALL")
    if status != "OK":
        imap.logout()
        raise RuntimeError("IMAP UID search failed")

    uids = data[0].split()[-limit:]
    results: list[dict] = []

    for uid in reversed(uids):
        uid_str = uid.decode() if isinstance(uid, (bytes, bytearray)) else str(uid)

        status, msg_data = imap.uid("fetch", uid, "(RFC822.HEADER FLAGS)")
        if status != "OK" or not msg_data or not msg_data[0]:
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subject = _decode_mime_header(msg.get("Subject"))
        from_ = _decode_mime_header(msg.get("From"))
        date_ = msg.get("Date")

        flags_blob = (
            msg_data[0][0].decode(errors="ignore")
            if isinstance(msg_data[0][0], (bytes, bytearray))
            else str(msg_data[0][0])
        )
        is_read = "\\Seen" in flags_blob

        results.append(
            {
                "provider_msg_id": uid_str,  # ✅ UID
                "subject": subject,
                "from_addr": from_,
                "date_raw": date_,
                "is_read": is_read,
            }
        )

    imap.logout()
    return results


def _uid_from_message_id(imap, message_id: str) -> str | None:
    """
    If DB stored Message-ID like <abc@domain>, find UID via IMAP search.
    """
    msgid = message_id.strip()
    # IMAP search likes raw header content, keep <> if present
    status, data = imap.uid("search", None, f'(HEADER Message-ID "{msgid}")')
    if status != "OK" or not data or not data[0]:
        return None
    uids = data[0].split()
    if not uids:
        return None
    uid = uids[-1]
    return uid.decode() if isinstance(uid, (bytes, bytearray)) else str(uid)


def fetch_full_message(cfg: ImapAccountConfig, provider_msg_id: str) -> dict:
    """
    Fetch full email body using either:
    - UID (digits) OR
    - Message-ID header (<...>) fallback.
    """
    imap = _connect(cfg)
    imap.login(cfg.email, cfg.password)
    imap.select(cfg.mailbox)

    uid = None
    if provider_msg_id and provider_msg_id.isdigit():
        uid = provider_msg_id
    else:
        uid = _uid_from_message_id(imap, provider_msg_id)

    if not uid:
        imap.logout()
        raise RuntimeError(f"Could not resolve UID for provider_msg_id={provider_msg_id!r}")

    status, data = imap.uid("fetch", uid, "(RFC822 FLAGS)")
    if status != "OK" or not data or not data[0]:
        imap.logout()
        raise RuntimeError(f"IMAP UID fetch failed for uid={uid}")

    raw_bytes = data[0][1]
    msg = email.message_from_bytes(raw_bytes)

    subject = _decode_mime_header(msg.get("Subject"))
    from_ = _decode_mime_header(msg.get("From"))
    date_ = msg.get("Date")

    body_text, body_html = _extract_text_and_html(msg)

    flags_blob = (
        data[0][0].decode(errors="ignore")
        if isinstance(data[0][0], (bytes, bytearray))
        else str(data[0][0])
    )
    is_read = "\\Seen" in flags_blob

    imap.logout()
    return {
        "uid": uid,
        "subject": subject,
        "from_addr": from_,
        "date_raw": date_,
        "body_text": body_text,
        "body_html": body_html,
        "is_read": is_read,
    }
