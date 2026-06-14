"""Gmail SMTP mail sender (synchronous, via smtplib)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from otis.config import MailSettings, get_settings
from otis.logging import get_logger

logger = get_logger(__name__)


class MailSender:
    """Sends emails through Gmail's SMTP server with STARTTLS."""

    def __init__(self, settings: MailSettings | None = None) -> None:
        self._settings = settings or get_settings().mail

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        attachment: Path | None = None,
    ) -> None:
        message = EmailMessage()
        message["From"] = self._settings.sender or self._settings.username
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        if attachment is not None:
            message.add_attachment(
                attachment.read_bytes(),
                maintype="application",
                subtype="zip",
                filename=attachment.name,
            )

        logger.info("Sending email to %s (subject=%r)", to, subject)
        with smtplib.SMTP(self._settings.host, self._settings.port) as smtp:
            smtp.starttls()
            if self._settings.username:
                smtp.login(self._settings.username, self._settings.password)
            smtp.send_message(message)
        logger.info("Email sent to %s", to)
