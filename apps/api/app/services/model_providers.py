from __future__ import annotations


PROVIDER_PREFIX_MAP = {
    "alibaba-bailian": "dashscope",
    "dashscope": "dashscope",
    "openai": "openai",
    "anthropic": "anthropic",
    "azure-openai": "azure",
    "google": "gemini",
    "vertex-ai": "vertex_ai",
    "deepseek": "deepseek",
    "minimax": "minimax",
    "moonshot": "moonshot",
}


PROVIDER_DISPLAY_OPTIONS = [
    {"label": "阿里百炼", "value": "alibaba-bailian", "vendor": "Alibaba"},
    {"label": "DashScope", "value": "dashscope", "vendor": "Alibaba"},
    {"label": "OpenAI", "value": "openai", "vendor": "OpenAI"},
    {"label": "Anthropic", "value": "anthropic", "vendor": "Anthropic"},
    {"label": "DeepSeek", "value": "deepseek", "vendor": "DeepSeek"},
    {"label": "MiniMax", "value": "minimax", "vendor": "MiniMax"},
    {"label": "月之暗面", "value": "moonshot", "vendor": "Moonshot"},
]


def get_provider_prefix(provider: str) -> str:
    normalized = (provider or "").strip().lower()
    return PROVIDER_PREFIX_MAP.get(normalized, normalized)


def build_litellm_model_name(provider: str, model_id: str) -> str:
    normalized_model_id = (model_id or "").strip()
    if not normalized_model_id:
        return ""
    provider_prefix = get_provider_prefix(provider)
    if provider_prefix == "dashscope" and "/" in normalized_model_id:
        normalized_model_id = normalized_model_id.split("/")[-1]
    if "/" in normalized_model_id:
        return normalized_model_id
    return f"{provider_prefix}/{normalized_model_id}"
