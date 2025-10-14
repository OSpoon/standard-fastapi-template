import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import emails  # type: ignore
from api_exception import (
    logger,
)
from jinja2 import Template

from app.core.config import settings
from app.models.apikey_model import APIKey, ExpiryDays


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


def generate_update_apikey_email(
    email_to: str,
    api_key_name: str,
    api_key_prefix: str,
    updated_at: str,
    new_expires_info: str,
    status: str,
    changes_summary: str,
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - API Key 已更新"

    # 根据状态设置颜色
    status_color = "#28a745" if status == "激活" else "#6c757d"

    html_content = render_email_template(
        template_name="update_apikey.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "email": email_to,
            "api_key_name": api_key_name,
            "api_key_prefix": api_key_prefix,
            "updated_at": updated_at,
            "new_expires_info": new_expires_info,
            "status": status,
            "status_color": status_color,
            "changes_summary": changes_summary,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_delete_apikey_email(
    email_to: str,
    api_key_name: str,
    api_key_prefix: str,
    deleted_at: str,
    created_at: str,
    last_used_info: str,
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - API Key 已删除"
    html_content = render_email_template(
        template_name="delete_apikey.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "email": email_to,
            "api_key_name": api_key_name,
            "api_key_prefix": api_key_prefix,
            "deleted_at": deleted_at,
            "created_at": created_at,
            "last_used_info": last_used_info,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_api_key() -> tuple[str, str]:
    """
    生成 API Key 和其前缀
    格式: sk-<random_string>
    """
    # 使用项目设置中的前缀，如果没有设置则使用默认前缀
    prefix = getattr(settings, "API_KEY_PREFIX", "sk")

    # 生成随机字符串
    alphabet = string.ascii_letters + string.digits
    random_string = "".join(secrets.choice(alphabet) for _ in range(48))

    # 组合完整的 API Key
    full_key = f"{prefix}-{random_string}"

    return full_key, prefix


def calculate_expiry_date(expiry_days: ExpiryDays) -> datetime:
    """
    根据天数档位计算过期时间
    """
    return datetime.now() + timedelta(days=expiry_days.value)


def is_api_key_valid(api_key: APIKey) -> bool:
    """
    检查 API Key 是否有效
    """
    # 检查是否激活
    if not api_key.is_active:
        return False

    # 检查是否过期
    if api_key.expires_at and api_key.expires_at < datetime.now():
        return False

    return True
