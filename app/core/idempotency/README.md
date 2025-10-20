# 幂等性模块完整说明文档

## 目录

1. [概述](#概述)
2. [核心原理](#核心原理)
3. [架构设计](#架构设计)
4. [模块结构](#模块结构)
5. [幂等流程](#幂等流程)
6. [使用指南](#使用指南)
7. [配置说明](#配置说明)
8. [高级用法](#高级用法)
9. [故障处理](#故障处理)
10. [性能优化](#性能优化)
11. [最佳实践](#最佳实践)

---

## 概述

幂等性模块是一个用于 FastAPI 的分布式幂等性解决方案,确保在分布式环境下,相同的请求不会被重复处理,即使客户端多次发送相同的请求(如网络重试、用户重复点击等)。

### 核心特性

- **完全无状态**: 不依赖全局配置,通过装饰器参数显式传递所有依赖
- **模块化设计**: 职责分离,易于测试和维护
- **可插拔后端**: 支持多种存储后端(Redis、内存等)
- **灵活的错误处理**: 支持自定义回调函数处理各种错误场景
- **并发安全**: 使用分布式锁防止并发请求冲突
- **响应缓存**: 自动缓存并重放成功的响应

### 适用场景

- **支付订单创建**: 防止用户重复点击导致重复扣款
- **数据写入操作**: 避免网络重试导致数据重复插入
- **外部 API 调用**: 防止因超时重试导致的重复调用
- **消息队列消费**: 确保消息幂等处理

---

## 核心原理

### 1. 幂等性概念

幂等性(Idempotency)是指:对于同一个请求,无论执行多少次,其效果都与执行一次相同。

```
f(x) = result
f(f(x)) = f(x) = result  // 多次执行结果相同
```

### 2. 请求唯一标识

通过 **幂等性密钥(Idempotency-Key)** 唯一标识一个请求:

```http
POST /api/orders HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{"product_id": 123, "quantity": 1}
```

### 3. 请求签名机制

除了幂等性密钥,还会生成 **请求签名** 来确保请求内容的一致性:

```python
签名 = SHA256(
    method +
    url +
    selected_headers +
    SHA256(body)
)
```

这确保了:

- 相同的 Idempotency-Key 必须对应相同的请求内容
- 如果请求内容变化,会检测到签名不匹配并拒绝

### 4. 三态记录模型

每个幂等性记录有三种状态:

```python
@dataclass
class IdempotencyRecord:
    signature: str              # 请求签名
    in_progress: bool = False   # 是否正在处理
    response: StoredResponse | None = None  # 缓存的响应
```

- **不存在**: 首次请求
- **in_progress=True**: 请求正在处理中
- **response 不为空**: 请求已完成,有缓存响应

---

## 架构设计

### 设计原则

1. **单一职责**: 每个模块只负责一项功能
2. **依赖注入**: 不依赖全局状态,通过参数传递依赖
3. **开放扩展**: 支持自定义后端和回调
4. **无侵入性**: 通过装饰器集成,不影响原有代码

### 模块分层

```
┌─────────────────────────────────────────┐
│         Decorator Layer                 │  装饰器层 - 对外接口
│         (decorator.py)                  │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Handler Layer                   │  处理层 - 业务逻辑
│  (handlers.py)                          │
│  - handle_existing_record               │
│  - wait_and_return_result               │
│  - execute_and_store                    │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Service Layer                   │  服务层 - 工具函数
│  (utils.py, serializers.py)            │
│  - extract_request_response             │
│  - build_request_signature              │
│  - serialize/deserialize                │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Backend Layer                   │  存储层 - 数据持久化
│  (backends/)                            │
│  - BaseIdempotencyBackend               │
│  - RedisIdempotencyBackend              │
└─────────────────────────────────────────┘
```

---

## 模块结构

### 文件组织

```
app/core/idempotency/
├── __init__.py              # 公共接口导出
├── decorator.py             # 主装饰器实现
├── handlers.py              # 记录处理逻辑
├── serializers.py           # 序列化工具
├── utils.py                 # 工具函数
├── callbacks.py             # 错误处理回调
├── exceptions.py            # 自定义异常
├── types.py                 # 类型定义
├── backends/
│   ├── base.py             # 抽象后端接口
│   └── redis_backend.py    # Redis 后端实现
└── README.md               # 本文档
```

### 核心模块说明

#### 1. decorator.py - 装饰器

**职责**: 提供 `@idempotent` 装饰器,协调整个幂等性流程

**核心函数**:

```python
def idempotent(
    backend: BaseIdempotencyBackend | None = None,
    header_name: str = "Idempotency-Key",
    wait_timeout_ms: int = 3000,
    lock_ttl_ms: int = 5000,
    record_ttl_ms: int = 86400000,
    on_key_missing: Callable | None = None,
    on_signature_mismatch: Callable | None = None,
    on_in_progress: Callable | None = None,
) -> Callable
```

#### 2. handlers.py - 处理器

**职责**: 实现幂等性核心业务逻辑

**核心函数**:

- `wait_for_completion()`: 等待其他进程完成处理
- `handle_existing_record()`: 处理已存在的幂等性记录
- `wait_and_return_result()`: 等待并返回结果
- `handle_wait_timeout()`: 处理等待超时
- `execute_and_store()`: 执行函数并存储结果
- `apply_cached_response()`: 应用缓存的响应

#### 3. serializers.py - 序列化

**职责**: 处理请求/响应的序列化和反序列化

**核心函数**:

- `serialize_result()`: 序列化函数执行结果
- `deserialize_stored_response()`: 反序列化存储的响应

#### 4. utils.py - 工具函数

**职责**: 提供通用工具函数

**核心函数**:

- `extract_request_response()`: 从参数中提取 Request 和 Response 对象
- `build_request_signature()`: 构建请求签名
- `get_request_body_bytes()`: 获取请求体字节

#### 5. callbacks.py - 回调函数

**职责**: 错误处理和回调机制

**核心函数**:

- `raise_key_missing_error_async()`: 处理缺少幂等性密钥
- `raise_signature_mismatch_error_async()`: 处理签名不匹配
- `raise_in_progress_error_async()`: 处理请求处理中
- `default_on_*()`: 默认回调实现

#### 6. backends/ - 存储后端

**职责**: 提供数据持久化接口

**接口定义**:

```python
class BaseIdempotencyBackend(ABC):
    async def acquire_lock(self, key: str, ttl_ms: int) -> bool
    async def release_lock(self, key: str) -> None
    async def get_record(self, key: str) -> IdempotencyRecord | None
    async def set_record(self, key: str, record: IdempotencyRecord, ttl_s: int) -> None
```

---

## 幂等流程

### 完整流程图

```
客户端请求 (带 Idempotency-Key)
    ↓
┌──────────────────────────────────────┐
│  1. 提取幂等性密钥                    │
│     - 从请求头获取 Idempotency-Key    │
│     - 验证密钥存在性                  │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  2. 构建请求签名                      │
│     - 计算请求内容哈希                │
│     - 生成签名: SHA256(内容)          │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  3. 检查已存在记录                    │
│     record = backend.get_record(key)  │
└──────────────────────────────────────┘
    ↓
    ├─── 记录存在? ───┐
    │                 ↓
    NO            ┌──────────────────────────┐
    │             │ 3.1 签名匹配?             │
    │             └──────────────────────────┘
    │                 ↓
    │                 ├─── YES ───┐
    │                 │            ↓
    │                 │        ┌─────────────────────┐
    │                 │        │ in_progress?        │
    │                 │        └─────────────────────┘
    │                 │            ↓
    │                 │            ├─── YES ───→ 等待完成
    │                 │            │
    │                 │            NO
    │                 │            ↓
    │                 │        ┌─────────────────────┐
    │                 │        │ 有缓存响应?          │
    │                 │        │ response != None    │
    │                 │        └─────────────────────┘
    │                 │            ↓
    │                 │            YES → 返回缓存响应
    │                 │
    │                 NO
    │                 ↓
    │             抛出签名不匹配异常
    │
    ↓
┌──────────────────────────────────────┐
│  4. 获取分布式锁                      │
│     locked = backend.acquire_lock()   │
└──────────────────────────────────────┘
    ↓
    ├─── 获锁成功? ───┐
    │                 │
    YES               NO → 等待其他进程完成
    ↓
┌──────────────────────────────────────┐
│  5. 写入处理中标记                    │
│     record.in_progress = True         │
│     backend.set_record(key, record)   │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  6. 执行业务函数                      │
│     result = await func(*args)        │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  7. 序列化结果                        │
│     body_bytes = serialize(result)    │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  8. 存储完整响应                      │
│     record.in_progress = False        │
│     record.response = stored_response │
│     backend.set_record(key, record)   │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│  9. 释放锁                            │
│     backend.release_lock(key)         │
└──────────────────────────────────────┘
    ↓
返回结果给客户端
```

### 并发请求处理

当多个相同请求并发到达时:

```
时间线:
t0: Request A 到达 → 获取锁成功 → 开始处理
t1: Request B 到达 → 获取锁失败 → 进入等待
t2: Request C 到达 → 获取锁失败 → 进入等待
t3: Request A 完成 → 存储响应 → 释放锁
t4: Request B 检测到完成 → 返回缓存响应
t5: Request C 检测到完成 → 返回缓存响应
```

**等待机制**: 采用轮询 + 退避策略

```python
delay = 0.05s  # 初始延迟
max_delay = 0.5s  # 最大延迟
每次循环: delay = min(max_delay, delay * 1.5)
最大等待: wait_timeout_ms (默认 3000ms)
```

---

## 使用指南

### 基础使用

#### 1. 配置后端

```python
import redis.asyncio as aioredis
from app.core.idempotency import RedisIdempotencyBackend

# 创建异步 Redis 客户端
redis_client = aioredis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=False  # 使用二进制存储更高效
)

# 或者使用连接 URL
redis_client = await aioredis.from_url(
    "redis://localhost:6379/0",
    decode_responses=False
)

# 创建幂等性后端
backend = RedisIdempotencyBackend(
    redis=redis_client,
    prefix="idem:"  # 键前缀
)
```

**推荐: 使用依赖注入**

在实际项目中,建议使用 FastAPI 的依赖注入来管理 Redis 连接:

```python
# app/api/deps.py
import redis.asyncio as aioredis
from app.core.config import settings

async def get_redis_client() -> aioredis.Redis:
    """获取 Redis 客户端"""
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=False
    )

# app/api/v1/endpoints/orders.py
from fastapi import Depends
from app.api.deps import get_redis_client
from app.core.idempotency import RedisIdempotencyBackend

@router.post("/orders")
@idempotent(
    backend=RedisIdempotencyBackend(
        redis=aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0
        ),
        prefix="idem:order:"
    )
)
async def create_order(
    request: Request,
    response: Response,
    data: OrderCreate
):
    """创建订单 - 确保幂等性"""
    order = await order_service.create(data)
    return {"order_id": order.id, "status": "created"}
```

#### 2. 应用装饰器

**简单使用**:

```python
from fastapi import APIRouter, Request, Response
from app.core.idempotency import idempotent

router = APIRouter()

@router.post("/orders")
@idempotent(backend=backend)
async def create_order(
    request: Request,
    response: Response,
    data: OrderCreate
):
    """创建订单 - 确保幂等性"""
    # 业务逻辑
    order = await order_service.create(data)
    return {"order_id": order.id, "status": "created"}
```

#### 3. 客户端调用

```python
import httpx
import uuid

# 生成幂等性密钥(建议使用 UUID)
idempotency_key = str(uuid.uuid4())

response = httpx.post(
    "http://api.example.com/orders",
    headers={"Idempotency-Key": idempotency_key},
    json={"product_id": 123, "quantity": 1}
)

# 重试时使用相同的密钥
if response.status_code >= 500:
    # 网络错误,使用相同密钥重试
    response = httpx.post(
        "http://api.example.com/orders",
        headers={"Idempotency-Key": idempotency_key},  # 相同的密钥
        json={"product_id": 123, "quantity": 1}
    )
```

### 响应头信息

成功的幂等请求会返回额外的响应头:

```http
HTTP/1.1 200 OK
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
X-Idempotency-Signature: a7f3d9e2c8b4f1a6e5d8c9b7a4f2e1d3
X-Idempotency-Status: hit  # 或 new, conflict, wait-timeout
```

**状态说明**:

- `new`: 首次处理,新建记录
- `hit`: 缓存命中,返回已存储的响应
- `conflict`: 签名不匹配,请求内容冲突
- `wait-timeout`: 等待超时

---

## 配置说明

### 装饰器参数

```python
@idempotent(
    backend=backend,              # 必需: 存储后端实例
    header_name="Idempotency-Key",  # 可选: 请求头名称
    wait_timeout_ms=3000,         # 可选: 等待超时(毫秒)
    lock_ttl_ms=5000,             # 可选: 锁过期时间(毫秒)
    record_ttl_ms=86400000,       # 可选: 记录 TTL(毫秒,默认24小时)
    on_key_missing=None,          # 可选: 缺少密钥回调
    on_signature_mismatch=None,   # 可选: 签名不匹配回调
    on_in_progress=None,          # 可选: 处理中回调
)
```

### 参数详解

| 参数                    | 类型                     | 默认值              | 说明                                  |
| ----------------------- | ------------------------ | ------------------- | ------------------------------------- |
| `backend`               | `BaseIdempotencyBackend` | **必需**            | 存储后端实例                          |
| `header_name`           | `str`                    | `"Idempotency-Key"` | 幂等性密钥的请求头名称                |
| `wait_timeout_ms`       | `int`                    | `3000`              | 等待其他请求完成的最大时间(毫秒)      |
| `lock_ttl_ms`           | `int`                    | `5000`              | 分布式锁的过期时间(毫秒),防止死锁     |
| `record_ttl_ms`         | `int`                    | `86400000`          | 幂等记录的缓存时间(毫秒),默认 24 小时 |
| `on_key_missing`        | `Callable`               | `None`              | 缺少幂等性密钥时的回调函数            |
| `on_signature_mismatch` | `Callable`               | `None`              | 请求签名不匹配时的回调函数            |
| `on_in_progress`        | `Callable`               | `None`              | 请求正在处理且等待超时时的回调        |

### 环境变量配置

在 `.env` 文件中配置:

```bash
# 幂等性配置
IDEMPOTENCY_KEY_HEADER="Idempotency-Key"
IDEMPOTENCY_LOCK_TTL_MS=30000
IDEMPOTENCY_RECORD_TTL_MS=3600000  # 1小时
IDEMPOTENCY_WAIT_TIMEOUT_MS=5000
```

在 `app/core/config.py` 中使用:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    IDEMPOTENCY_KEY_HEADER: str = "Idempotency-Key"
    IDEMPOTENCY_LOCK_TTL_MS: int = 30_000
    IDEMPOTENCY_RECORD_TTL_MS: int = 3_600_000
    IDEMPOTENCY_WAIT_TIMEOUT_MS: int = 5_000
```

---

## 高级用法

### 自定义错误处理

#### 1. 自定义缺少密钥处理

```python
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

async def custom_on_key_missing(request: Request, response: Response):
    """自定义处理:返回 400 而不是抛出异常"""
    response.status_code = status.HTTP_400_BAD_REQUEST
    # 可以记录日志
    logger.warning(f"Missing idempotency key for {request.url}")
    # 返回自定义错误消息
    return JSONResponse(
        status_code=400,
        content={
            "error": "IDEMPOTENCY_KEY_REQUIRED",
            "message": "请在请求头中提供 Idempotency-Key"
        }
    )

@router.post("/orders")
@idempotent(
    backend=backend,
    on_key_missing=custom_on_key_missing
)
async def create_order(request: Request, response: Response, data: OrderCreate):
    ...
```

#### 2. 自定义签名不匹配处理

```python
async def custom_on_signature_mismatch(
    request: Request,
    response: Response,
    headers: dict[str, str]
):
    """签名不匹配:记录警告并拒绝请求"""
    logger.error(
        f"Signature mismatch for key {headers.get('Idempotency-Key')}"
    )
    response.status_code = status.HTTP_409_CONFLICT
    response.headers.update(headers)
    return JSONResponse(
        status_code=409,
        content={
            "error": "SIGNATURE_MISMATCH",
            "message": "相同的幂等性密钥不能用于不同的请求内容"
        }
    )

@router.post("/orders")
@idempotent(
    backend=backend,
    on_signature_mismatch=custom_on_signature_mismatch
)
async def create_order(...):
    ...
```

#### 3. 自定义处理中等待

```python
async def custom_on_in_progress(
    request: Request,
    response: Response,
    retry_after: int,
    headers: dict[str, str]
):
    """处理中:返回 429 要求客户端重试"""
    response.status_code = status.HTTP_429_TOO_MANY_REQUESTS
    response.headers["Retry-After"] = str(retry_after)
    response.headers.update(headers)
    return JSONResponse(
        status_code=429,
        content={
            "error": "REQUEST_IN_PROGRESS",
            "message": f"请求正在处理中,请在 {retry_after} 秒后重试",
            "retry_after": retry_after
        }
    )
```

### 自定义存储后端

实现自己的存储后端(如 PostgreSQL):

```python
from app.core.idempotency.backends.base import BaseIdempotencyBackend
from app.core.idempotency.types import IdempotencyRecord

class PostgresIdempotencyBackend(BaseIdempotencyBackend):
    def __init__(self, db_session):
        self.db = db_session

    async def acquire_lock(self, key: str, ttl_ms: int) -> bool:
        """使用 PostgreSQL 行锁实现"""
        try:
            await self.db.execute(
                "SELECT pg_try_advisory_lock(hashtext(:key))",
                {"key": key}
            )
            return True
        except Exception:
            return False

    async def release_lock(self, key: str) -> None:
        await self.db.execute(
            "SELECT pg_advisory_unlock(hashtext(:key))",
            {"key": key}
        )

    async def get_record(self, key: str) -> IdempotencyRecord | None:
        result = await self.db.fetch_one(
            "SELECT data FROM idempotency_records WHERE key = :key",
            {"key": key}
        )
        if result:
            return self.deserialize_record(result["data"])
        return None

    async def set_record(
        self,
        key: str,
        record: IdempotencyRecord,
        ttl_s: int
    ) -> None:
        data = self.serialize_record(record)
        await self.db.execute(
            """
            INSERT INTO idempotency_records (key, data, expires_at)
            VALUES (:key, :data, NOW() + INTERVAL ':ttl seconds')
            ON CONFLICT (key) DO UPDATE SET data = :data
            """,
            {"key": key, "data": data, "ttl": ttl_s}
        )
```

### 条件性应用幂等性

某些情况下,你可能希望根据条件决定是否应用幂等性:

```python
def conditional_idempotent(condition: Callable):
    """条件装饰器工厂"""
    def decorator(func):
        # 应用幂等装饰器
        idempotent_func = idempotent(backend=backend)(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 检查条件
            if await condition(*args, **kwargs):
                return await idempotent_func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

async def is_production(request: Request, *args, **kwargs):
    """仅在生产环境启用幂等性"""
    return settings.ENVIRONMENT == "production"

@router.post("/orders")
@conditional_idempotent(is_production)
async def create_order(...):
    ...
```

---

## 故障处理

### 常见错误场景

#### 1. 缺少幂等性密钥

**错误**: `IdempotencyKeyMissingError`

**原因**: 请求头中未提供 `Idempotency-Key`

**解决方案**:

```python
# 客户端确保添加请求头
headers = {"Idempotency-Key": str(uuid.uuid4())}
response = httpx.post(url, headers=headers, json=data)
```

#### 2. 签名不匹配

**错误**: `IdempotencySignatureMismatchError`

**原因**: 相同的幂等性密钥用于不同的请求内容

**示例**:

```python
# 第一次请求
requests.post(url, headers={"Idempotency-Key": "key-123"},
              json={"amount": 100})

# 第二次请求 - 内容不同!
requests.post(url, headers={"Idempotency-Key": "key-123"},  # 相同的 key
              json={"amount": 200})  # 不同的内容!
# ❌ 抛出 IdempotencySignatureMismatchError
```

**解决方案**:

- 每次不同的请求使用不同的幂等性密钥
- 重试时使用相同的密钥和相同的请求内容

#### 3. 请求处理中超时

**错误**: `IdempotencyInProgressError`

**原因**: 另一个相同的请求正在处理中,等待超时

**解决方案**:

```python
# 客户端处理重试
import time

max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        response = httpx.post(url, headers=headers, json=data)
        break
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:  # Too Many Requests
            retry_after = int(e.response.headers.get("Retry-After", 1))
            time.sleep(retry_after)
            retry_count += 1
        else:
            raise
```

#### 4. 后端连接失败

**错误**: Redis/数据库连接错误

**解决方案**:

```python
# 使用连接池和重试机制
import redis.asyncio as aioredis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

redis_client = aioredis.Redis(
    host="localhost",
    port=6379,
    db=0,
    retry=Retry(ExponentialBackoff(), 3),
    socket_connect_timeout=5,
    socket_keepalive=True,
    decode_responses=False,
)
```

### 监控和告警

#### 1. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

async def monitored_on_signature_mismatch(
    request: Request,
    response: Response,
    headers: dict[str, str]
):
    """记录签名不匹配事件"""
    logger.warning(
        "Idempotency signature mismatch",
        extra={
            "idempotency_key": headers.get("Idempotency-Key"),
            "path": str(request.url),
            "method": request.method,
        }
    )
    raise IdempotencySignatureMismatchError(headers=headers)
```

#### 2. 指标收集

```python
from prometheus_client import Counter, Histogram

idempotency_requests = Counter(
    'idempotency_requests_total',
    'Total idempotency requests',
    ['status']  # new, hit, conflict
)

idempotency_duration = Histogram(
    'idempotency_wait_duration_seconds',
    'Wait duration for idempotent requests'
)

# 在 handlers.py 中使用
async def handle_existing_record(...):
    if record.response is not None:
        idempotency_requests.labels(status='hit').inc()
        return apply_cached_response(...)
```

---

## 性能优化

### 1. 选择合适的 TTL

**记录 TTL (record_ttl_ms)**:

- 设置过长: 占用存储空间,可能返回过时的响应
- 设置过短: 无法应对延迟重试,失去幂等保护

**建议**:

- **支付订单**: 24-48 小时
- **一般 API**: 1-6 小时
- **高频操作**: 5-30 分钟

```python
@idempotent(
    backend=backend,
    record_ttl_ms=3600000  # 1小时,根据业务调整
)
```

### 2. 优化锁超时

**锁 TTL (lock_ttl_ms)**:

- 应该大于接口处理时间的上限
- 防止进程崩溃导致死锁

**建议**:

```python
# 快速接口(< 1s)
lock_ttl_ms=5000  # 5秒

# 中速接口(1-5s)
lock_ttl_ms=10000  # 10秒

# 慢速接口(5-30s)
lock_ttl_ms=60000  # 60秒
```

### 3. 批量操作优化

对于批量操作,考虑使用粗粒度的幂等性密钥:

```python
@router.post("/orders/batch")
@idempotent(backend=backend)
async def create_orders_batch(
    request: Request,
    response: Response,
    orders: list[OrderCreate]
):
    """批量创建订单"""
    # 整个批次使用一个幂等性密钥
    results = []
    for order_data in orders:
        order = await order_service.create(order_data)
        results.append(order)
    return {"orders": results}
```

### 4. Redis 优化

```python
import redis.asyncio as aioredis

# 使用连接池
redis_client = aioredis.Redis(
    host="localhost",
    port=6379,
    db=0,
    max_connections=50,  # 连接池大小
    decode_responses=False,  # 二进制存储更高效
)

# 使用 Redis Cluster 提高可用性
from redis.asyncio.cluster import RedisCluster

redis_client = RedisCluster(
    startup_nodes=[
        {"host": "redis-1", "port": 6379},
        {"host": "redis-2", "port": 6379},
    ],
    decode_responses=False,
)
```

---

## 最佳实践

### 1. 幂等性密钥生成

**推荐方式**:

```python
import uuid

# ✅ 使用 UUID v4(随机)
idempotency_key = str(uuid.uuid4())

# ✅ 使用业务相关的唯一标识
idempotency_key = f"order-{user_id}-{timestamp}-{nonce}"

# ❌ 避免使用可预测的值
idempotency_key = "order-123"  # 太简单,容易冲突
```

**客户端密钥管理**:

```python
class IdempotentClient:
    def __init__(self):
        self.key_store = {}  # 存储请求 -> 密钥映射

    def post(self, url: str, data: dict):
        # 生成请求唯一标识
        request_id = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

        # 重用已存在的密钥(用于重试)
        if request_id in self.key_store:
            key = self.key_store[request_id]
        else:
            key = str(uuid.uuid4())
            self.key_store[request_id] = key

        return httpx.post(
            url,
            headers={"Idempotency-Key": key},
            json=data
        )
```

### 2. 何时使用幂等性

**✅ 应该使用**:

- 写操作(POST, PUT, PATCH)
- 有副作用的操作(创建订单、扣款、发送邮件)
- 对外部系统的调用

**❌ 不需要使用**:

- 纯读操作(GET 请求)
- 内部查询接口
- 无副作用的操作

### 3. 与事务结合

```python
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/transfer")
@idempotent(backend=backend)
async def transfer_money(
    request: Request,
    response: Response,
    data: TransferRequest,
    db: AsyncSession = Depends(get_db)
):
    """转账操作 - 幂等性 + 数据库事务"""
    async with db.begin():  # 开启事务
        # 扣款
        await db.execute(
            "UPDATE accounts SET balance = balance - :amount WHERE id = :id",
            {"amount": data.amount, "id": data.from_account}
        )
        # 入账
        await db.execute(
            "UPDATE accounts SET balance = balance + :amount WHERE id = :id",
            {"amount": data.amount, "id": data.to_account}
        )
        # 记录流水
        transfer = Transfer(
            from_account=data.from_account,
            to_account=data.to_account,
            amount=data.amount
        )
        db.add(transfer)

    return {"transfer_id": transfer.id, "status": "completed"}
```

### 4. 错误处理策略

```python
@router.post("/orders")
@idempotent(backend=backend, record_ttl_ms=3600000)
async def create_order(
    request: Request,
    response: Response,
    data: OrderCreate
):
    try:
        # 业务逻辑
        order = await order_service.create(data)
        return {"order_id": order.id}
    except BusinessException as e:
        # 业务异常也应该被缓存(避免重复尝试)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 系统异常不缓存(可以重试)
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 5. 测试建议

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_idempotency():
    """测试幂等性"""
    # 准备
    backend = AsyncMock(spec=BaseIdempotencyBackend)
    backend.get_record.return_value = None
    backend.acquire_lock.return_value = True

    # 第一次调用
    response1 = await create_order(
        request=mock_request(headers={"idempotency-key": "test-key"}),
        response=Response(),
        data=OrderCreate(product_id=1, quantity=1)
    )

    # 模拟缓存命中
    backend.get_record.return_value = IdempotencyRecord(
        signature="sig123",
        response=StoredResponse(
            status_code=200,
            headers={},
            body=b'{"order_id": 1}'
        )
    )

    # 第二次调用 - 应返回缓存结果
    response2 = await create_order(
        request=mock_request(headers={"idempotency-key": "test-key"}),
        response=Response(),
        data=OrderCreate(product_id=1, quantity=1)
    )

    assert response1 == response2  # 结果相同
    assert backend.set_record.call_count == 2  # 存储了两次(进行中 + 完成)
```

---

## 总结

### 优势

1. **防止重复处理**: 确保相同请求只执行一次
2. **提高可靠性**: 自动处理网络重试、用户误操作等场景
3. **改善用户体验**: 避免重复扣款、重复下单等问题
4. **无侵入性**: 通过装饰器轻松集成,不影响原有代码
5. **高度可配置**: 支持自定义后端、回调、超时等
6. **模块化设计**: 职责清晰,易于维护和扩展

### 注意事项

1. **幂等性密钥唯一性**: 确保每个独立请求使用不同的密钥
2. **请求内容一致性**: 重试时必须使用相同的请求内容
3. **合理的 TTL**: 根据业务特点设置记录缓存时间
4. **后端可用性**: 依赖 Redis 等外部服务,需要确保高可用
5. **性能影响**: 每个请求需要额外的存储操作,注意监控性能
6. **异常处理**: 区分业务异常和系统异常,合理设计缓存策略

### 适用边界

**适合使用**:

- 金融交易、订单创建等关键操作
- 对外部系统的调用(支付、短信等)
- 需要严格防重的写操作

**不适合使用**:

- 高频读操作
- 内部查询接口
- 对性能要求极高的场景(考虑性能开销)
