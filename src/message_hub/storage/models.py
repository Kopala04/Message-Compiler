from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))  # gmail|outlook|imap
    email: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    auth_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.utcnow())

    folders: Mapped[list["Folder"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("provider", "email", name="uq_accounts_provider_email"),)


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))

    provider_folder_id: Mapped[str] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(256))

    account: Mapped["Account"] = relationship(back_populates="folders")
    messages: Mapped[list["Message"]] = relationship(back_populates="folder", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("account_id", "provider_folder_id", name="uq_folders_account_provider_id"),)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id", ondelete="CASCADE"))

    provider_msg_id: Mapped[str] = mapped_column(String(256))
    thread_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    from_addr: Mapped[str | None] = mapped_column(String(512), nullable=True)
    to_addrs: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    date_utc: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.utcnow())

    account: Mapped["Account"] = relationship(back_populates="messages")
    folder: Mapped["Folder"] = relationship(back_populates="messages")

    __table_args__ = (UniqueConstraint("account_id", "provider_msg_id", name="uq_messages_account_provider_msg_id"),)


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id", ondelete="CASCADE"))

    cursor: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_sync_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("account_id", "folder_id", name="uq_syncstate_account_folder"),)
