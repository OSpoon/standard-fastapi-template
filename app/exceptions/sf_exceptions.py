"""
自定义异常代码
"""

from api_exception import BaseExceptionCode


# 自定义异常代码
class SFExceptionCode(BaseExceptionCode):
    """自定义异常代码类"""

    ITEM_NOT_FOUND = ("ITM-404", "Item not found")
    INCORRECT_EMAIL_OR_PASSWORD = ("AUTH-401", "Incorrect email or password.")
    # 统一未认证/凭证缺失或无效时的错误码与文案
    UNAUTHORIZED = (
        "AUTH-401",
        "Unauthorized",
        "Authentication credentials were missing or invalid.",
    )
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

    # API Key 相关异常
    APIKEY_NOT_FOUND = ("APIKEY-404", "API Key not found.")
    CREATE_APIKEY_ERROR = ("APIKEY-500", "Failed to create API Key.")
    UPDATE_APIKEY_ERROR = ("APIKEY-501", "Failed to update API Key.")
    INVALID_APIKEY = ("APIKEY-401", "Invalid API Key.")
    APIKEY_EXPIRED = ("APIKEY-402", "API Key has expired.")
    APIKEY_INACTIVE = ("APIKEY-403", "API Key is inactive.")
    APIKEY_RATE_LIMIT_EXCEEDED = ("APIKEY-429", "Too Many Requests.")
