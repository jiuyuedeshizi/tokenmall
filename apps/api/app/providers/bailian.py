from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.core.config import settings


@dataclass(frozen=True)
class BailianProviderConfig:
    base_url: str
    native_api_base: str
    api_key: str
    headers: dict[str, str] = field(default_factory=dict)


def _derive_native_api_base(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.netloc:
        return "https://dashscope.aliyuncs.com/api/v1"
    return f"{parsed.scheme}://{parsed.netloc}/api/v1"


def get_bailian_provider_config() -> BailianProviderConfig:
    return BailianProviderConfig(
        base_url=settings.bailian_api_base,
        native_api_base=_derive_native_api_base(settings.bailian_api_base),
        api_key=settings.bailian_api_key,
    )
