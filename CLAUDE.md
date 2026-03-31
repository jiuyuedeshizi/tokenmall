# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

TokenMall 是一个基于 Next.js + FastAPI + PostgreSQL + Redis + Docker 的 Token 售卖与 API 管理平台。

## 代码架构

```
tokenmall/
├── apps/
│   ├── web/        # Next.js 16 前端 (React 19, Tailwind 4)
│   ├── api/        # FastAPI Python 后端 + NestJS 脚手架
│   └── proxy/      # 代理服务
├── packages/       # 共享包 (billing, common, db, sdk)
├── infra/
│   └── docker/     # Docker Compose 文件
│       ├── docker-compose.dev.yml   # 本地开发 (PostgreSQL, Redis)
│       └── docker-compose.yml       # 生产部署
└── billing/, common/, db/, sdk/    # 预留包目录
```

## 开发命令

### 根目录 (monorepo)
```bash
pnpm dev:deps        # 启动 Docker 依赖 (PostgreSQL, Redis)
pnpm dev:deps:down   # 停止 Docker 依赖
pnpm dev:web         # 启动 Next.js 开发服务器 (http://localhost:3000)
pnpm lint:web        # Lint web 应用
pnpm typecheck:web   # 类型检查 web 应用
pnpm dev:api         # 启动 FastAPI 开发服务器 (http://localhost:8000)
```

### 各应用
```bash
# Web (Next.js)
cd apps/web && pnpm dev

# API (FastAPI) - 需要 Python venv
cd apps/api
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker (全栈)
```bash
cd infra/docker
docker compose --env-file ../../.env up --build
```

## 环境变量

将 `.env.example` 复制为 `.env` 并配置：
- `BAILIAN_API_KEY` - API 代理必需
- `DATABASE_URL` - PostgreSQL 连接字符串
- `REDIS_URL` - Redis 连接字符串
- `JWT_SECRET` - JWT 签名密钥
- `NEXT_PUBLIC_API_URL` - API 基础 URL (默认: http://localhost:8000)

## 核心依赖

- **Provider APIs** - 直连官方 OpenAI-compatible 接口
- **PostgreSQL** (localhost:5432) - 主数据库
- **Redis** (localhost:6379) - 缓存和会话

## 默认管理员

- 邮箱: `admin@tokenmall.dev`
- 密码: `Admin123456`

## API 测试

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer tk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen-plus", "messages": [{"role": "user", "content": "你好"}]}'
```

## 技术栈

- **前端**: Next.js 16, React 19, Tailwind CSS 4, TypeScript
- **后端**: FastAPI (Python), SQLAlchemy, Alembic 数据库迁移
- **数据库**: PostgreSQL + pg 驱动
- **缓存**: Redis
- **模型代理**: 官方 OpenAI-compatible 透明代理
- **包管理器**: pnpm 10.28.2
