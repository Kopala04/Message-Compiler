from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtCore import Qt


class MessageDetail(QWidget):
    def __init__(self):
        super().__init__()

        self.subject = QLabel()
        self.subject.setStyleSheet("font-weight: bold; font-size: 16px")

        self.from_ = QLabel()
        self.date = QLabel()

        self.body = QTextEdit()
        self.body.setReadOnly(True)
        # Ensure HTML content is accepted and rendered
        self.body.setAcceptRichText(True)

        layout = QVBoxLayout()
        layout.addWidget(self.subject)
        layout.addWidget(self.from_)
        layout.addWidget(self.date)
        layout.addWidget(self.body)
        self.setLayout(layout)

        self.clear()

    def clear(self):
        self.subject.setText("Select a message…")
        self.from_.setText("")
        self.date.setText("")
        self.body.setPlainText("")

    def set_message(self, msg):
        self.subject.setText(msg.subject or "(no subject)")
        self.from_.setText(f"From: {msg.from_addr or 'unknown'}")
        self.date.setText(f"Date: {msg.date_utc or ''}")

        # Get body content - preserve None vs empty string distinction
        body_html = getattr(msg, "body_html", None)
        body_text = getattr(msg, "body_text", None)
        snippet = getattr(msg, "snippet", None)
        
        # Process body content: strip whitespace only if content exists
        html = None
        text = None
        snippet_str = None
        
        if body_html:
            html_stripped = body_html.strip()
            if html_stripped:  # Only use if non-empty after stripping
                html = html_stripped
                
        if body_text:
            text_stripped = body_text.strip()
            if text_stripped:  # Only use if non-empty after stripping
                text = text_stripped
                
        if snippet:
            snippet_stripped = snippet.strip()
            if snippet_stripped:  # Only use if non-empty after stripping
                snippet_str = snippet_stripped

        # Display in priority order: HTML > text > snippet > no body
        if html:
            # Use setHtml for HTML content - QTextEdit should render HTML with formatting
            # Note: Images and external resources may not load, but basic HTML/styling should work
            self.body.setHtml(html)
        elif text:
            self.body.setPlainText(text)
        elif snippet_str:
            self.body.setPlainText(snippet_str)
        else:
            self.body.setPlainText("(No body found)")
