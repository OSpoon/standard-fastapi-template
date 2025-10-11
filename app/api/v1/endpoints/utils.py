from api_exception import (
    ResponseModel,
    logger,
)
from fastapi import APIRouter
from pydantic.networks import EmailStr

from app.utils import generate_test_email, send_email

router = APIRouter()


@router.post(
    "/test-email/",
    status_code=201,
)
def test_email(email_to: EmailStr) -> ResponseModel[str]:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return ResponseModel(data="Test email sent")


@router.get("/health-check/")
async def health_check() -> ResponseModel[bool]:
    """健康检查端点，检查API是否运行"""
    logger.info("Health check request received")
    return ResponseModel(data=True)
