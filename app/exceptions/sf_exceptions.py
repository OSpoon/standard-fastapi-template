"""
自定义异常代码
"""

from api_exception import BaseExceptionCode


# 自定义异常代码
class SFExceptionCode(BaseExceptionCode):
    """自定义异常代码类"""

    ITEM_NOT_FOUND = ("ITM-404", "Item not found.")
