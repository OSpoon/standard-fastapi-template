from sqlmodel import SQLModel


# Generic message
class Message(SQLModel):
    message: str


# Idempotency key response
class IdempotencyKeyResponse(SQLModel):
    """幂等性密钥响应模型"""

    idempotency_key: str  # SHA-256 哈希值（64 字符）
    expires_in: int  # 密钥有效期（秒）
    generated_at: str  # 生成时间（ISO 格式）
