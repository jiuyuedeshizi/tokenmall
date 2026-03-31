# TokenMall MVP

基于 `Next.js + FastAPI + PostgreSQL + Docker` 的 token 售卖与 API 管理平台。

## 功能

- 用户注册、登录
- 余额充值与模拟支付
- API Key 创建、启停、额度控制
- 模型库展示
- 使用历史与账单
- 管理员查看用户、订单、API Key
- 通过 `/v1/chat/completions` 透明代理官方 OpenAI-compatible 模型接口并按 token 实时扣费

## 本地开发

推荐前期用“本机跑前后端，Docker 只跑依赖”的方式，这样前端热更新和后端调试都会快很多。

### 1. 准备环境变量

```bash
cp .env.example .env
```

至少需要填写：

```env
BAILIAN_API_KEY=你的阿里百炼API Key
TENCENT_API_KEY=你的腾讯API Key（如需启用腾讯 provider）
```

### 2. 启动依赖服务

只启动 `PostgreSQL / Redis`。这个命令会使用 [docker-compose.dev.yml](/Users/jh/projects/tokenmall/infra/docker/docker-compose.dev.yml)：

```bash
pnpm dev:deps
```

服务地址：

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

停止依赖服务：

```bash
pnpm dev:deps:down
```

### 3. 本机启动 FastAPI

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env .env
cd ../..
```

然后在项目根目录执行：

```bash
pnpm dev:api
```

后端地址：

- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`

### 4. 本机启动 Next.js

```bash
cd apps/web
pnpm install
cd ../..
pnpm dev:web
```

前端地址：

- Web: `http://localhost:3000`

### 5. 全部 Docker 启动

如果你要验证完整容器化环境，仍然可以使用：

```bash
cd infra/docker
docker compose --env-file ../../.env up --build
```

说明：

- [docker-compose.dev.yml](/Users/jh/projects/tokenmall/infra/docker/docker-compose.dev.yml) 只负责本地开发依赖
- [docker-compose.yml](/Users/jh/projects/tokenmall/infra/docker/docker-compose.yml) 保留完整部署链路，包含 `web` 和 `api`

### 默认管理员

- 邮箱: `admin@tokenmall.dev`
- 密码: `Admin123456`

## API 测试

先在控制台中创建 API Key，然后调用：

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer tk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-plus",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

## 说明

- 当前支付链路为 MVP 模拟支付，保留了真实支付订单结构
- 模型价格来自本地种子数据，可继续扩展
- API Key 明文只在创建时返回一次
- 推荐开发模式是：本机跑 `web/api`，Docker 只跑 `postgres/redis`
