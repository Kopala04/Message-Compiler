import sys
import datetime as dt


from PySide6.QtCore import Qt, QTimer, QThreadPool, QSignalBlocker
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSplitter,
    QToolBar,
    QStyle,
)

from message_hub.connectors.imap_connector import ImapAccountConfig, fetch_full_message
from message_hub.services.imap_sync import sync_imap_headers
from message_hub.services.message_repo import get_latest_messages_sqlite
from message_hub.services.message_actions import (
    get_message_sqlite,
    get_account_email_sqlite,
    mark_read_sqlite,
    save_body_sqlite,
    update_provider_msg_id_sqlite,
)
from message_hub.storage.db import DatabaseConfig, make_engine, make_session_factory
from message_hub.storage.models import Base
from message_hub.ui.imap_dialog import ImapAccountDialog
from message_hub.ui.message_detail import MessageDetail
from message_hub.ui.workers import FunctionWorker


def _message_sort_key(m) -> tuple:
    d = getattr(m, "date_utc", None) or getattr(m, "created_at", None)
    return (d or dt.datetime.min, getattr(m, "id", 0))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # DB
        self.cfg = DatabaseConfig()
        self.engine = make_engine(self.cfg)
        Base.metadata.create_all(self.engine)
        self.SessionFactory = make_session_factory(self.engine)

        # State
        self.messages = []
        self.newest_message_id: int | None = None
        self.active_imap_accounts: list[ImapAccountConfig] = []
        self.threadpool = QThreadPool.globalInstance()
        self.sync_in_progress = False

        # UI
        self.list_widget = QListWidget()
        self.detail = MessageDetail()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        # Divider lines + padding
        self.list_widget.setStyleSheet(
            """
            QListWidget { outline: 0; }
            QListWidget::item {
                border-bottom: 1px solid rgba(0,0,0,0.18);
                padding: 8px;
            }
            QListWidget::item:selected {
                background: rgba(0, 120, 215, 0.20);
            }
            """
        )

        tb = QToolBar("Actions")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction("Add IMAP + Sync").triggered.connect(self.add_imap_and_sync)
        tb.addAction("Refresh").triggered.connect(self.refresh)

        self.list_widget.currentItemChanged.connect(self.on_item_selected)

        # Bulb icon
        self.icon_new = QIcon.fromTheme("emblem-new")
        if self.icon_new.isNull():
            self.icon_new = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)

        # Auto sync
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.auto_tick)
        self.timer.start()

        self.refresh()

    # --------------------------
    # Auto sync (threaded)
    # --------------------------
    def auto_tick(self):
        if self.sync_in_progress:
            return

        if not self.active_imap_accounts:
            self.refresh_if_changed()
            return

        self.sync_in_progress = True
        worker = FunctionWorker(self._sync_all_accounts)
        worker.signals.finished.connect(self._on_auto_sync_finished)
        worker.signals.error.connect(self._on_auto_sync_error)
        self.threadpool.start(worker)

    def _sync_all_accounts(self):
        total = {"fetched": 0, "inserted": 0, "skipped": 0}
        with self.SessionFactory() as session:
            for cfg in self.active_imap_accounts:
                stats = sync_imap_headers(session, cfg, limit=50)
                total["fetched"] += stats["fetched"]
                total["inserted"] += stats["inserted"]
                total["skipped"] += stats["skipped"]
        return total

    def _on_auto_sync_finished(self, stats: dict):
        self.sync_in_progress = False
        if stats.get("inserted", 0) > 0:
            self.refresh()
        else:
            self.refresh_if_changed()

    def _on_auto_sync_error(self, err_text: str):
        self.sync_in_progress = False
        self.setWindowTitle(f"Message Hub – Sync error: {err_text}")

    def refresh_if_changed(self):
        latest = get_latest_messages_sqlite(self.cfg.db_path, limit=1)
        newest_id = int(latest[0].id) if latest else None
        if newest_id != self.newest_message_id:
            self.refresh()

    # --------------------------
    # Refresh list (IMPORTANT: block signals to avoid recursion)
    # --------------------------
    def refresh(self):
        # preserve selected message id
        selected_id = None
        cur = self.list_widget.currentItem()
        if cur is not None:
            selected_id = cur.data(Qt.ItemDataRole.UserRole)

        self.messages = get_latest_messages_sqlite(self.cfg.db_path, limit=200)
        if self.messages:
            self.messages.sort(key=_message_sort_key, reverse=True)
            self.newest_message_id = int(self.messages[0].id)
        else:
            self.newest_message_id = None

        self.setWindowTitle(f"Message Hub – Inbox ({len(self.messages)} msgs) | Auto: 5s")

        # ✅ This prevents currentItemChanged from firing while we rebuild the list
        blocker = QSignalBlocker(self.list_widget)

        self.list_widget.clear()
        self.detail.clear()

        if not self.messages:
            self.list_widget.addItem(QListWidgetItem("No messages yet. Click 'Add IMAP + Sync' to import."))
            return

        restore_row = None
        for i, m in enumerate(self.messages):
            subject = m.subject or "(no subject)"
            from_ = m.from_addr or "unknown"
            date = m.date_utc or ""
            if hasattr(date, "strftime"):
                date = date.strftime("%Y-%m-%d %H:%M")

            item = QListWidgetItem(f"{subject}  |  {from_}  |  {date}")
            item.setData(Qt.ItemDataRole.UserRole, int(m.id))

            # bulb on newest unread
            if (int(m.id) == self.newest_message_id) and (not bool(m.is_read)):
                item.setIcon(self.icon_new)

            self.list_widget.addItem(item)

            if selected_id is not None and int(m.id) == int(selected_id):
                restore_row = i

        if restore_row is not None:
            self.list_widget.setCurrentRow(restore_row)
        else:
            self.list_widget.setCurrentRow(0)

        # blocker automatically unblocks here when it goes out of scope
        _ = blocker  # (keeps linter calm)

    # --------------------------
    # Selection: fetch body + mark read (NO refresh() call here!)
    # --------------------------
    def on_item_selected(self, current, previous=None):
        if current is None:
            self.detail.clear()
            return

        message_id = current.data(Qt.ItemDataRole.UserRole)
        if message_id is None:
            self.detail.clear()
            return

        mid = int(message_id)

        msg = get_message_sqlite(self.cfg.db_path, mid)
        if not msg:
            self.detail.clear()
            return

        # Lazy-load body if missing
        body_text = getattr(msg, "body_text", None)
        body_html = getattr(msg, "body_html", None)
        # Check if body exists: None means not fetched yet, empty string means fetched but empty
        # We only want to fetch if it's None (never been fetched)
        needs_fetch = body_text is None and body_html is None
        
        if needs_fetch:
            cfg = self._find_imap_cfg_for_message(mid)
            if cfg:
                try:
                    provider_msg_id = str(getattr(msg, "provider_msg_id", ""))
                    if provider_msg_id:
                        data = fetch_full_message(cfg, provider_msg_id=provider_msg_id)

                        # Save body (can be None or empty string - both are valid)
                        save_body_sqlite(
                            self.cfg.db_path,
                            mid,
                            data.get("body_text"),  # Keep None if not present
                            data.get("body_html"),  # Keep None if not present
                        )

                        # ✅ self-heal: store UID if connector resolved it
                        uid = data.get("uid")
                        if uid and str(uid).isdigit():
                            update_provider_msg_id_sqlite(self.cfg.db_path, mid, str(uid))

                except Exception as e:
                    QMessageBox.warning(self, "Body fetch failed", repr(e))

        # Always reload message before displaying to ensure we have latest data
        msg = get_message_sqlite(self.cfg.db_path, mid)
        if not msg:
            self.detail.clear()
            return

        # Mark read on open
        if not bool(getattr(msg, "is_read", False)):
            mark_read_sqlite(self.cfg.db_path, mid)
            msg = get_message_sqlite(self.cfg.db_path, mid) or msg
            # ✅ Update bulb/icons without rebuilding list (no recursion)
            self._update_bulb_icons()

        self.detail.set_message(msg)

    def _update_bulb_icons(self):
        """
        Recompute newest unread and update list item icons without triggering selection recursion.
        """
        # reload newest data quickly (sqlite)
        self.messages = get_latest_messages_sqlite(self.cfg.db_path, limit=200)
        if self.messages:
            self.messages.sort(key=_message_sort_key, reverse=True)
            self.newest_message_id = int(self.messages[0].id)
        else:
            self.newest_message_id = None

        blocker = QSignalBlocker(self.list_widget)

        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            mid = item.data(Qt.ItemDataRole.UserRole)
            if mid is None:
                item.setIcon(QIcon())
                continue

            # find message state
            m = next((x for x in self.messages if int(x.id) == int(mid)), None)
            if not m:
                item.setIcon(QIcon())
                continue

            if (int(m.id) == int(self.newest_message_id)) and (not bool(m.is_read)):
                item.setIcon(self.icon_new)
            else:
                item.setIcon(QIcon())

        _ = blocker

    def _find_imap_cfg_for_message(self, message_id: int) -> ImapAccountConfig | None:
        """Find IMAP config for a specific message by matching account email."""
        if not self.active_imap_accounts:
            return None
        
        # Try to get account email from the message
        account_email = get_account_email_sqlite(self.cfg.db_path, message_id)
        if account_email:
            # Match by email
            for cfg in self.active_imap_accounts:
                if cfg.email == account_email:
                    return cfg
        
        # Fallback to last account if no match
        return self.active_imap_accounts[-1]
    
    def _find_imap_cfg_for_current_session(self) -> ImapAccountConfig | None:
        if not self.active_imap_accounts:
            return None
        return self.active_imap_accounts[-1]

    # --------------------------
    # Add IMAP + sync
    # --------------------------
    def add_imap_and_sync(self):
        dlg = ImapAccountDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.get_values()
        if not data["host"] or not data["email"] or not data["password"]:
            QMessageBox.warning(self, "Missing info", "Host, email, and password are required.")
            return

        cfg = ImapAccountConfig(
            host=data["host"],
            email=data["email"],
            password=data["password"],
            mailbox=data["mailbox"],
        )

        self.active_imap_accounts = [a for a in self.active_imap_accounts if a.email != cfg.email]
        self.active_imap_accounts.append(cfg)

        try:
            with self.SessionFactory() as session:
                stats = sync_imap_headers(session, cfg, limit=50)
        except Exception as e:
            QMessageBox.critical(self, "Sync failed", repr(e))
            return

        QMessageBox.information(
            self,
            "Sync complete",
            f"Fetched {stats['fetched']}\nInserted {stats['inserted']}\nSkipped {stats['skipped']}",
        )
        self.refresh()


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 700)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
