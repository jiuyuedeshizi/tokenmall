from dataclasses import dataclass, field

from app.core.config import settings


@dataclass(frozen=True)
class BailianProviderConfig:
    base_url: str
    api_key: str
    headers: dict[str, str] = field(default_factory=dict)


def get_bailian_provider_config() -> BailianProviderConfig:
    return BailianProviderConfig(
        base_url=settings.bailian_api_base,
        api_key=settings.bailian_api_key,
    )
