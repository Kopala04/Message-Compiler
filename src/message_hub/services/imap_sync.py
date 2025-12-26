from __future__ import annotations

import datetime as dt
from email.utils import parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from message_hub.connectors.imap_connector import ImapAccountConfig, fetch_latest_headers
from message_hub.storage.models import Account, Folder, Message


def _parse_date_to_utc(date_raw: str | None) -> dt.datetime | None:
    if not date_raw:
        return None
    try:
        d = parsedate_to_datetime(date_raw)
        if d.tzinfo is None:
            return d  # best effort
        return d.astimezone(dt.timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def get_or_create_account(session: Session, provider: str, email: str) -> Account:
    stmt = select(Account).where(Account.provider == provider, Account.email == email)
    acc = session.execute(stmt).scalar_one_or_none()
    if acc:
        return acc
    acc = Account(provider=provider, email=email, display_name=None, auth_json=None)
    session.add(acc)
    session.commit()
    session.refresh(acc)
    return acc


def get_or_create_folder(session: Session, account_id: int, provider_folder_id: str, name: str) -> Folder:
    stmt = select(Folder).where(
        Folder.account_id == account_id,
        Folder.provider_folder_id == provider_folder_id,
    )
    folder = session.execute(stmt).scalar_one_or_none()
    if folder:
        return folder
    folder = Folder(account_id=account_id, provider_folder_id=provider_folder_id, name=name)
    session.add(folder)
    session.commit()
    session.refresh(folder)
    return folder


def sync_imap_headers(session: Session, cfg: ImapAccountConfig, limit: int = 30) -> dict:
    account = get_or_create_account(session, provider="imap", email=cfg.email)
    folder = get_or_create_folder(
        session, account_id=account.id, provider_folder_id=cfg.mailbox, name=cfg.mailbox
    )

    items = fetch_latest_headers(cfg, limit=limit)

    inserted = 0
    skipped = 0

    for it in items:
        msg = Message(
            account_id=account.id,
            folder_id=folder.id,
            provider_msg_id=it["provider_msg_id"],
            thread_id=None,
            from_addr=it.get("from_addr"),
            to_addrs=None,
            subject=it.get("subject"),
            snippet=None,
            date_utc=_parse_date_to_utc(it.get("date_raw")),
            body_text=None,
            body_html=None,
            is_read=bool(it.get("is_read", False)),  # ✅ FIX
        )
        session.add(msg)
        try:
            session.commit()
            inserted += 1
        except IntegrityError:
            session.rollback()
            skipped += 1

    return {"inserted": inserted, "skipped": skipped, "fetched": len(items)}
