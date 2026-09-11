"""Email dispatch tool (SMTP).

Lets the executive-outreach agent actually deliver the final job-search
digest to ``kenono2000@gmail.com`` instead of merely printing it.  SMTP
settings are read from environment variables (loaded via ``python-dotenv``
in ``config.py``):

* ``SMTP_HOST``     e.g. ``smtp.gmail.com``
* ``SMTP_PORT``     e.g. ``587``
* ``SMTP_USER``     the account email address
* ``SMTP_PASS``     app password / token
* ``SMTP_FROM``     sender address (defaults to ``SMTP_USER``)
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from crewai.tools import BaseTool


class EmailDispatchTool(BaseTool):
    name: str = "Email Dispatch (SMTP)"
    description: str = (
        "Sends an email via SMTP. Provide recipient, subject, text_body and "
        "(optionally) html_body. Credentials are taken from SMTP_HOST, "
        "SMTP_PORT, SMTP_USER, SMTP_PASS and SMTP_FROM environment variables. "
        "Returns a JSON status string."
    )

    def _smtp_params(self) -> dict[str, Any]:
        return {
            "host": os.getenv("SMTP_HOST", ""),
            "port": int(os.getenv("SMTP_PORT", "587") or "587"),
            "user": os.getenv("SMTP_USER", ""),
            "password": os.getenv("SMTP_PASS", ""),
            "from_addr": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER", ""),
        }

    def _run(
        self,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> str:
        params = self._smtp_params()

        missing = [
            name
            for name, val in (
                ("SMTP_HOST", params["host"]),
                ("SMTP_USER", params["user"]),
                ("SMTP_PASS", params["password"]),
            )
            if not val
        ]
        if missing:
            return json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": (
                        "SMTP credentials are not configured. "
                        f"Missing env vars: {', '.join(missing)}. "
                        "Populate SMTP_HOST, SMTP_USER, SMTP_PASS "
                        "(and optionally SMTP_PORT, SMTP_FROM)."
                    ),
                },
                ensure_ascii=False,
            )

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = params["from_addr"]
        message["To"] = recipient
        message.attach(MIMEText(text_body, "plain", "utf-8"))
        if html_body:
            message.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            port = params["port"]
            with smtplib.SMTP(params["host"], port, timeout=30) as server:
                server.starttls(context=context)
                server.login(params["user"], params["password"])
                server.sendmail(params["from_addr"], recipient, message.as_string())
        except (smtplib.SMTPException, OSError) as exc:
            return json.dumps(
                {
                    "status": "FAILED",
                    "reason": "SMTP send raised an exception.",
                    "error": repr(exc),
                    "recipient": recipient,
                    "subject": subject,
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "status": "SENT",
                "recipient": recipient,
                "subject": subject,
                "host": params["host"],
                "port": port,
                "message_bytes": len(message.as_string().encode("utf-8")),
            },
            ensure_ascii=False,
            indent=2,
        )
