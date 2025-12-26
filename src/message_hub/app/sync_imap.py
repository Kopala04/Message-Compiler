import getpass

from message_hub.connectors.imap_connector import ImapAccountConfig
from message_hub.services.imap_sync import sync_imap_headers
from message_hub.storage.db import DatabaseConfig, make_engine, make_session_factory
from message_hub.storage.models import Base


def main():
    host = input("IMAP host (e.g. imap.gmail.com): ").strip()
    email_ = input("Email: ").strip()
    password = getpass.getpass("Password (or app password): ")
    mailbox = input("Mailbox [INBOX]: ").strip() or "INBOX"
    limit = int(input("How many to fetch [30]: ").strip() or "30")

    cfg = ImapAccountConfig(host=host, email=email_, password=password, mailbox=mailbox)

    engine = make_engine(DatabaseConfig())
    Base.metadata.create_all(engine)
    SessionFactory = make_session_factory(engine)

    with SessionFactory() as session:
        stats = sync_imap_headers(session, cfg, limit=limit)

    print("Done:", stats)


if __name__ == "__main__":
    main()
