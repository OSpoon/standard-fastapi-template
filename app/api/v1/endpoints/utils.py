import hashlib
import secrets
import time
import uuid
from typing import Annotated

from api_exception import APIException, ResponseModel, logger
from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.api.deps import get_redis_client
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.common_model import IdempotencyKeyResponse

router = APIRouter()


@router.get("/health-check/")
async def health_check() -> ResponseModel[bool]:
    """健康检查端点，检查API是否运行"""
    logger.info("Health check request received")
    return ResponseModel(data=True)


@router.post(
    "/generate-idempotency-key", response_model=ResponseModel[IdempotencyKeyResponse]
)
async def generate_idempotency_key(
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> ResponseModel[IdempotencyKeyResponse]:
    """
    生成高可用的幂等性密钥（Idempotency-Key）

    该接口采用多层策略确保密钥的全局唯一性和高可用性：

    1. **UUID v4**: 提供 128 位随机性（碰撞概率 < 10^-36）
    2. **纳秒级时间戳**: 确保时间维度的唯一性
    3. **分布式计数器**: Redis 原子递增操作，防止并发冲突
    4. **安全随机熵**: 64 字节（512 位）加密级随机数

    最终生成 64 字符的 SHA-256 哈希值，满足以下特性：
    - 全局唯一性：多数据中心部署下仍保证唯一
    - 不可预测性：无法通过逆向工程推测密钥
    - 分布式友好：Redis 集群模式下支持水平扩展
    - 时序可追溯：包含时间戳信息，便于审计

    **安全说明**：
    - 公开接口，无需认证（用于授权前获取密钥）
    - Redis 故障时自动降级（使用本地熵源）
    - 建议客户端在 24 小时内使用生成的密钥

    **返回示例**：
    ```json
    {
        "idempotency_key": "a7f3c8e9d2b1...",
        "expires_in": 86400,
        "generated_at": "2025-10-20T10:30:45.123456Z"
    }
    ```
    """
    try:
        # 1. 基础唯一标识：UUID v4（128 位随机）
        unique_id = str(uuid.uuid4())

        # 2. 纳秒级时间戳（确保时间维度唯一性）
        timestamp_ns = time.time_ns()

        # 3. 分布式计数器（Redis 原子操作，防并发冲突）
        counter_key = f"idempotency:counter:global:{timestamp_ns // 1_000_000_000}"
        try:
            counter = await redis.incr(counter_key)
            # 设置过期时间（1小时后自动清理）
            await redis.expire(counter_key, 3600)
        except Exception as redis_error:
            logger.warning(
                f"Redis counter failed, using fallback: {redis_error}",
            )
            # 降级方案：使用本地随机数代替计数器
            counter = secrets.randbits(64)

        # 4. 加密级随机熵（512 位安全随机数）
        random_entropy = secrets.token_hex(64)  # 64 bytes = 512 bits

        # 5. 组合所有熵源并生成最终密钥
        combined_entropy = f"{unique_id}:{timestamp_ns}:{counter}:{random_entropy}"

        # 使用 SHA-256 生成固定长度的密钥（64 字符十六进制）
        idempotency_key = hashlib.sha256(combined_entropy.encode("utf-8")).hexdigest()

        # 6. 记录生成日志（用于审计）
        logger.info(
            "Generated idempotency key",
            extra={
                "key_prefix": idempotency_key[:8],  # 只记录前缀，避免泄露
                "timestamp": timestamp_ns,
            },
        )

        # 7. 返回密钥及元数据
        return ResponseModel(
            data=IdempotencyKeyResponse(
                idempotency_key=idempotency_key,
                expires_in=86400,  # 24 小时（建议前端在此时间内使用）
                generated_at=time.strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(timestamp_ns / 1_000_000_000)
                ),
            )
        )

    except Exception as e:
        logger.error(
            f"Failed to generate idempotency key: {e}",
            exc_info=True,
        )
        raise APIException(
            error_code=SFExceptionCode.IDEMPOTENCY_KEY_GENERATION_FAILED,
        ) from e
