# TokenMall API

FastAPI 业务后端，负责：

- 用户注册登录
- 钱包余额与账本
- 充值订单与模拟支付
- API Key 生成、限额与启停
- 代理 LiteLLM 调用阿里百炼
- 按 token 实时扣费
- 管理员用户、订单、密钥管理

## 启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 环境变量

- `DATABASE_URL`
- `JWT_SECRET`
- `LITELLM_URL`
- `LITELLM_MASTER_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

服务启动时会自动建表并写入默认管理员和模型种子数据。
