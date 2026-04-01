from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tokenmall",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    jwt_secret: str = Field(default="change-me-jwt-secret", alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=60 * 24, alias="JWT_EXPIRE_MINUTES")
    bailian_api_key: str = Field(default="", alias="BAILIAN_API_KEY")
    bailian_api_base: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="BAILIAN_API_BASE",
    )
    tencent_api_key: str = Field(default="", alias="TENCENT_API_KEY")
    tencent_api_base: str = Field(default="", alias="TENCENT_API_BASE")
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )
    admin_email: str = Field(default="admin@tokenmall.dev", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="Admin123456", alias="ADMIN_PASSWORD")
    alipay_app_id: str = Field(default="", alias="ALIPAY_APP_ID")
    alipay_app_private_key_path: str = Field(default="", alias="ALIPAY_APP_PRIVATE_KEY_PATH")
    alipay_public_key_path: str = Field(default="", alias="ALIPAY_PUBLIC_KEY_PATH")
    alipay_server_url: str = Field(default="https://openapi.alipay.com/gateway.do", alias="ALIPAY_SERVER_URL")
    alipay_notify_url: str = Field(default="", alias="ALIPAY_NOTIFY_URL")
    alipay_return_url: str = Field(default="", alias="ALIPAY_RETURN_URL")
    wechat_app_id: str = Field(default="", alias="WECHAT_APP_ID")
    wechat_mch_id: str = Field(default="", alias="WECHAT_MCH_ID")
    wechat_private_key_path: str = Field(default="", alias="WECHAT_PRIVATE_KEY_PATH")
    wechat_cert_serial_no: str = Field(default="", alias="WECHAT_CERT_SERIAL_NO")
    wechat_apiv3_key: str = Field(default="", alias="WECHAT_APIV3_KEY")
    wechat_notify_url: str = Field(default="", alias="WECHAT_NOTIFY_URL")
    unionpay_merchant_id: str = Field(default="", alias="UNIONPAY_MERCHANT_ID")
    unionpay_sign_cert_path: str = Field(default="", alias="UNIONPAY_SIGN_CERT_PATH")
    unionpay_sign_cert_password: str = Field(default="", alias="UNIONPAY_SIGN_CERT_PASSWORD")
    unionpay_root_cert_path: str = Field(default="", alias="UNIONPAY_ROOT_CERT_PATH")
    unionpay_middle_cert_path: str = Field(default="", alias="UNIONPAY_MIDDLE_CERT_PATH")
    unionpay_front_url: str = Field(default="", alias="UNIONPAY_FRONT_URL")
    unionpay_back_url: str = Field(default="", alias="UNIONPAY_BACK_URL")
    unionpay_front_trans_url: str = Field(
        default="https://gateway.test.95516.com/gateway/api/frontTransReq.do",
        alias="UNIONPAY_FRONT_TRANS_URL",
    )
    unionpay_back_trans_url: str = Field(
        default="https://gateway.test.95516.com/gateway/api/backTransReq.do",
        alias="UNIONPAY_BACK_TRANS_URL",
    )
    unionpay_query_url: str = Field(
        default="https://gateway.test.95516.com/gateway/api/queryTrans.do",
        alias="UNIONPAY_QUERY_URL",
    )
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=40, alias="DB_MAX_OVERFLOW")
    db_pool_timeout_seconds: int = Field(default=30, alias="DB_POOL_TIMEOUT_SECONDS")
    db_pool_recycle_seconds: int = Field(default=1800, alias="DB_POOL_RECYCLE_SECONDS")
    proxy_http_connect_timeout_seconds: float = Field(default=5.0, alias="PROXY_HTTP_CONNECT_TIMEOUT_SECONDS")
    proxy_http_read_timeout_seconds: float = Field(default=120.0, alias="PROXY_HTTP_READ_TIMEOUT_SECONDS")
    proxy_http_write_timeout_seconds: float = Field(default=30.0, alias="PROXY_HTTP_WRITE_TIMEOUT_SECONDS")
    proxy_http_pool_timeout_seconds: float = Field(default=5.0, alias="PROXY_HTTP_POOL_TIMEOUT_SECONDS")
    proxy_stream_pending_limit_bytes: int = Field(default=262144, alias="PROXY_STREAM_PENDING_LIMIT_BYTES")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=465, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="TokenMall", alias="SMTP_FROM_NAME")
    smtp_use_ssl: bool = Field(default=True, alias="SMTP_USE_SSL")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")
    alibaba_cloud_access_key_id: str = Field(default="", alias="ALIBABA_CLOUD_ACCESS_KEY_ID")
    alibaba_cloud_access_key_secret: str = Field(default="", alias="ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    alibaba_cloud_sms_region: str = Field(default="cn-hangzhou", alias="ALIBABA_CLOUD_SMS_REGION")
    alibaba_cloud_sms_auth_enabled: bool = Field(default=False, alias="ALIBABA_CLOUD_SMS_AUTH_ENABLED")
    alibaba_cloud_sms_sign_name: str = Field(default="", alias="ALIBABA_CLOUD_SMS_SIGN_NAME")
    alibaba_cloud_sms_template_code: str = Field(default="", alias="ALIBABA_CLOUD_SMS_TEMPLATE_CODE")
    alibaba_cloud_sms_template_param: str = Field(
        default='{"code":"##code##","min":"5"}',
        alias="ALIBABA_CLOUD_SMS_TEMPLATE_PARAM",
    )
    alibaba_cloud_sms_scheme_name: str = Field(default="", alias="ALIBABA_CLOUD_SMS_SCHEME_NAME")
    alibaba_cloud_sms_debug_return_demo_code: bool = Field(
        default=True,
        alias="ALIBABA_CLOUD_SMS_DEBUG_RETURN_DEMO_CODE",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    def read_text_if_exists(self, file_path: str) -> str:
        if not file_path:
            return ""
        path = Path(file_path)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
