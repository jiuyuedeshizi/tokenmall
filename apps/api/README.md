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
- `JWT_SECRET`
- `BAILIAN_API_KEY`
- `BAILIAN_API_BASE`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

服务启动时只负责空环境建表前置、默认管理员和模型种子数据；业务表结构变更统一通过 Alembic 管理。
