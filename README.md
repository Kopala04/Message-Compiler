# 📬 Message Hub Desktop

**Message Hub Desktop** is a Python desktop application that aggregates emails from IMAP accounts into a single, unified inbox.  
It supports background syncing, unread indicators, and full email body rendering (HTML & text), all stored locally in SQLite.

This project was built as a **portfolio / CV project** to demonstrate clean architecture, desktop UI development, background workers, and real-world protocol integration (IMAP).

---

## ✨ Features

- 📥 IMAP email integration (Gmail supported)
- 🔄 Automatic background refresh (every 5 seconds)
- 💡 Unread indicator (bulb icon for newest unread message)
- 📖 Full email body loading (HTML & plain text)
- 🧠 Lazy loading (fetch body only when opened)
- 💾 Local persistence with SQLite
- 🖥️ Desktop UI built with PySide6 (Qt)
- 🔁 Safe UI updates (no recursion, signal blocking)
- 🧪 Clean separation of UI / services / connectors / storage

---

## 🧱 Architecture Overview


src/
├── message_hub/
│ ├── app/ # Application entry & main window
│ ├── ui/ # Qt UI components
│ ├── services/ # Business logic (sync, actions)
│ ├── connectors/ # IMAP protocol handling
│ ├── storage/ # Database config & ORM models
│ └── domain/ # Core domain models


- **UI Layer**: PySide6 widgets, signal-safe refresh logic
- **Service Layer**: Syncing, message actions, background workers
- **Connector Layer**: IMAP protocol abstraction
- **Storage Layer**: SQLite (via SQLAlchemy + sqlite3 for reads)

---

## 🛠 Tech Stack

- **Python 3.11**
- **PySide6 (Qt for Python)**
- **SQLite**
- **IMAP (imaplib)**
- **SQLAlchemy**
- **ThreadPool / Background workers**

---

## 🚀 Getting Started

### 1️⃣ Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/message-hub-desktop.git
cd message-hub-desktop


python -m venv .venv
.venv\Scripts\activate


pip install -e .


python -m message_hub.app.main #This RUNS the main program.

📧 Gmail IMAP Setup

To use Gmail, you must create an App Password:

Enable 2-Step Verification on your Google account

Go to Google Account → Security → App passwords

Create a new password for Mail

Use these settings in the app:

Host: imap.gmail.com
Mailbox: INBOX
Email: your_email@gmail.com
Password: (App Password)


⚠️ Your password is never committed and only lives in memory.

🔄 Reset Local Data (Optional)

To remove all locally cached messages:
python -c "from message_hub.storage.db import DatabaseConfig; print(DatabaseConfig().db_path)"

📌 Why This Project Matters

This project demonstrates:

Real-world protocol usage (IMAP)

Desktop UI engineering with Qt

Background threading & UI safety

Local persistence & data modeling

Debugging complex recursion and state issues

Production-style project structure

It is intentionally built beyond “toy examples” to reflect real application complexity.

🧠 Future Improvements

Multiple account selection in UI

Secure credential storage (keyring)

Message search & filtering

Attachments support

OAuth support for Gmail

📄 License

MIT License

👤 Author Sandro
Built by Sandro
(Portfolio / CV Project)
