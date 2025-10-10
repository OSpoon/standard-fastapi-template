"""
自定义异常代码
"""

from api_exception import BaseExceptionCode


# 自定义异常代码
class SFExceptionCode(BaseExceptionCode):
    """自定义异常代码类"""

    USER_NOT_FOUND = ("USR-404", "User not found.")
