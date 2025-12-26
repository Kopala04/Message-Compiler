from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
)


class ImapAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add IMAP Account")
        self.setModal(True)

        self.host = QLineEdit()
        self.host.setPlaceholderText("imap.gmail.com")

        self.email = QLineEdit()
        self.email.setPlaceholderText("your@email.com")

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        self.mailbox = QLineEdit()
        self.mailbox.setText("INBOX")

        form = QFormLayout()
        form.addRow("IMAP Host", self.host)
        form.addRow("Email", self.email)
        form.addRow("Password / App Password", self.password)
        form.addRow("Mailbox", self.mailbox)

        btn_ok = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        root = QVBoxLayout()
        root.addLayout(form)
        root.addLayout(btns)
        self.setLayout(root)

    def get_values(self) -> dict:
        return {
            "host": self.host.text().strip(),
            "email": self.email.text().strip(),
            "password": self.password.text(),
            "mailbox": self.mailbox.text().strip() or "INBOX",
        }
