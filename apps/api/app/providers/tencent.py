from dataclasses import dataclass, field

from app.core.config import settings


@dataclass(frozen=True)
class TencentProviderConfig:
    base_url: str
    api_key: str
    headers: dict[str, str] = field(default_factory=dict)


def get_tencent_provider_config() -> TencentProviderConfig:
    return TencentProviderConfig(
        base_url=settings.tencent_api_base,
        api_key=settings.tencent_api_key,
    )
