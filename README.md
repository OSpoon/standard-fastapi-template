# Standard FastAPI Template

一个基于 [APIException](https://github.com/akutayural/APIException) 构建的 [FastAPI](https://github.com/fastapi/fastapi) 项目模板，用于快速启动新的 API 项目。

## 特性

*   **Docker-centric 开发**: 完全基于 Docker 容器进行开发和部署。
*   **高效依赖管理**: 使用 [uv](https://astral.sh/uv) 进行快速、可靠的 Python 依赖管理。
*   **代码质量工具**: 集成 [ruff](https://docs.astral.sh/ruff/) 进行代码格式化和 linting。
*   **API 异常处理**: 基于 `APIException` 提供统一、可扩展的 API 异常处理机制。
*   **结构化项目布局**: 清晰的项目结构，便于团队协作和维护。

## 快速开始

### 先决条件

在开始之前，请确保您的系统已安装以下软件：

*   [Git](https://git-scm.com/)
*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### 克隆仓库

```bash
git clone https://github.com/ospoon/standard-fastapi-template.git
cd standard-fastapi-template
```

### 初始化环境

安装所有依赖项 (主要用于本地开发或 IDE 识别):

```bash
uv sync
```

### 启动项目

在本地开发模式下启动服务 (监听文件变化并自动重启)：

```bash
docker compose watch
```

服务将在 `http://localhost:8000` 启动。

### 访问 API 文档

启动服务后，可以通过以下 URL 访问 API 文档：

*   **Swagger UI**: `http://localhost:8000/api/v1/docs`
*   **ReDoc**: `http://localhost:8000/api/v1/redoc`

## 开发指南

### 项目结构

```
├── app/                        # FastAPI 应用程序代码目录
│   ├── alembic/                # Alembic 数据库迁移目录
│   ├── api/                    # API 路由和依赖目录
│   │   ├── deps.py             # 依赖注入文件
│   │   └── v1/                 # API 版本 1 目录
│   │       ├── endpoints/      # API 接口端点目录
│   │       │   ├── items.py    # 示例 API 路由文件
│   │       │   └── utils.py    # API 工具函数文件
│   │       └── api.py          # API 路由定义文件
│   ├── core/                   # 核心配置和数据库连接目录
│   │   ├── config.py           # 配置设置文件
│   │   └── db.py               # 数据库连接和会话文件
│   ├── exceptions/             # 异常处理模块目录
│   │   └── sf_exceptions.py    # 自定义异常文件
│   ├── crud.py                 # 数据库操作 (CRUD) 文件
│   ├── main.py                 # 应用入口点文件
│   └── models.py               # 数据模型定义文件
├── scripts/                    # 辅助脚本目录
│   ├── format.sh               # 格式化脚本
│   └── lint.sh                 # Linting 脚本
├── .env                        # 环境变量配置文件
├── alembic.ini                 # Alembic 配置文件
├── docker-compose.override.yml # Docker Compose 覆盖文件 (开发环境)
├── docker-compose.yml          # Docker Compose 主配置文件
├── Dockerfile                  # Docker 镜像构建文件
├── LICENSE                     # 许可证文件
├── pyproject.toml              # 项目依赖和工具配置文件
└── README.md                   # 项目说明文件
```

## 贡献

欢迎贡献！请遵循以下步骤：

1.  Fork 此仓库。
2.  创建您的特性分支 (`git checkout -b feature/your-feature-name`)。
3.  提交您的更改 (`git commit -m 'feat: Add some amazing feature'`)。
4.  推送到分支 (`git push origin feature/your-feature-name`)。
5.  打开一个 Pull Request。

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。
