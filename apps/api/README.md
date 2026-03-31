# TokenMall API

FastAPI 业务后端，负责：

- 用户注册登录
- 钱包余额与账本
- 充值订单与模拟支付
- API Key 生成、限额与启停
- 透明代理官方 OpenAI-compatible provider
- 按 token 实时扣费
- 管理员用户、订单、密钥管理

## 启动

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 测试

```bash
.venv/bin/python -m pytest tests -q
```

## 迁移

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
```

## 环境变量

- `DATABASE_URL`
- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `DB_POOL_TIMEOUT_SECONDS`
- `DB_POOL_RECYCLE_SECONDS`
- `JWT_SECRET`
- `BAILIAN_API_KEY`
- `BAILIAN_API_BASE`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `PROXY_HTTP_CONNECT_TIMEOUT_SECONDS`
- `PROXY_HTTP_READ_TIMEOUT_SECONDS`
- `PROXY_HTTP_WRITE_TIMEOUT_SECONDS`
- `PROXY_HTTP_POOL_TIMEOUT_SECONDS`
- `PROXY_STREAM_PENDING_LIMIT_BYTES`

推荐按下面这组参数作为生产起步值：

```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
PROXY_HTTP_CONNECT_TIMEOUT_SECONDS=5
PROXY_HTTP_READ_TIMEOUT_SECONDS=120
PROXY_HTTP_WRITE_TIMEOUT_SECONDS=30
PROXY_HTTP_POOL_TIMEOUT_SECONDS=5
PROXY_STREAM_PENDING_LIMIT_BYTES=262144
```

说明：

- `DB_POOL_*` 只对 PostgreSQL 这类连接池数据库生效，SQLite 会自动跳过。
- `PROXY_HTTP_*` 控制转发到上游模型服务时的连接、读取、写入和连接池等待超时。
- `PROXY_STREAM_PENDING_LIMIT_BYTES` 用来限制流式 SSE 解析时单次未完成缓冲的最大字节数，避免无换行上游导致内存持续增长。

服务启动时只负责空环境建表前置、默认管理员和模型种子数据；业务表结构变更统一通过 Alembic 管理。
