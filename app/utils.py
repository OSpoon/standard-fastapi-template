from dataclasses import dataclass
from pathlib import Path
from typing import Any

import emails  # type: ignore
from api_exception import (
    logger,
)
from jinja2 import Template

from app.core.config import settings


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "templates" / "email" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def generate_new_apikey_email(
    email_to: str, api_key_name: str, api_key: str, created_at: str, expires_info: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - 新的 API Key 已创建"
    html_content = render_email_template(
        template_name="new_apikey.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "email": email_to,
            "api_key_name": api_key_name,
            "api_key": api_key,
            "created_at": created_at,
            "expires_info": expires_info,
            "status": "激活",
        },
    )
    return EmailData(html_content=html_content, subject=subject)
