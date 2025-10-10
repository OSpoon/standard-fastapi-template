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

安装所有依赖项

```bash
uv sync
```

激活虚拟环境

```bash
source .venv/bin/activate
```

### 启动项目

在监听模式下启动服务：

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
├── app/                     # FastAPI 应用程序代码
│   ├── __init__.py
│   ├── config/              # 应用配置
│   ├── exceptions/          # 异常处理模块
│   ├── main.py              # 应用入口点
│   ├── models/              # 数据模型定义
│   └── routers/             # API 路由定义
├── docker-compose.override.yml # Docker Compose 覆盖文件 (开发环境)
├── docker-compose.yml       # Docker Compose 主配置文件
├── pyproject.toml           # 项目依赖和工具配置
├── scripts/                 # 辅助脚本
│   ├── format.sh
│   └── lint.sh
├── uv.lock                  # uv 依赖锁定文件
├── .dockerignore
├── .env                     # 环境变量配置文件
├── .gitignore
├── .python-version
├── .vscode/                 # VS Code 配置
├── Dockerfile               # Docker 镜像构建文件
├── LICENSE
└── README.md
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
