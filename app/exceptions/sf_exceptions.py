"""
自定义异常代码
"""

from api_exception import BaseExceptionCode


# 自定义异常代码
class SFExceptionCode(BaseExceptionCode):
    """自定义异常代码类"""

    ITEM_NOT_FOUND = ("ITM-404", "Item not found")
    INCORRECT_EMAIL_OR_PASSWORD = ("AUTH-401", "Incorrect email or password.")
    USER_INACTIVE = ("USR-402", "Inactive user.")
    USER_EMAIL_NOT_FOUND = (
        "USR-403",
        "The user with this email does not exist in the system.",
    )
    USER_USERNAME_NOT_FOUND = (
        "USR-404",
        "The user with this username does not exist in the system.",
    )
    INVALID_TOKEN = ("AUTH-400", "Invalid token.")
    INVALID_CREDENTIALS = ("AUTH-403", "Could not validate credentials.")
    USER_NOT_FOUND = ("USR-405", "User not found.")
    EMAIL_ALREADY_EXISTS = (
        "USR-406",
        "The user with this email already exists in the system.",
    )
    NEW_PASSWORD_SAME_AS_CURRENT = (
        "AUTH-407",
        "New password cannot be the same as the current one.",
    )
    INSUFFICIENT_PRIVILEGES = ("AUTH-403", "The user doesn't have enough privileges.")
