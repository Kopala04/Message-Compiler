import getpass

from message_hub.connectors.imap_connector import ImapAccountConfig, fetch_latest_headers


def main():
    host = input("IMAP host (e.g. imap.gmail.com): ").strip()
    email_ = input("Email: ").strip()
    password = getpass.getpass("Password (or app password): ")
    mailbox = input("Mailbox [INBOX]: ").strip() or "INBOX"

    cfg = ImapAccountConfig(host=host, email=email_, password=password, mailbox=mailbox)
    items = fetch_latest_headers(cfg, limit=10)

    for i, m in enumerate(items, start=1):
        print(f"{i}. {m['subject']}  |  {m['from_addr']}  |  {m['date_raw']}")


if __name__ == "__main__":
    main()
