from __future__ import annotations

from decimal import Decimal
import json


def _token_prices(input_price: str, output_price: str) -> tuple[str, str]:
    return (str(Decimal(input_price).quantize(Decimal("0.0001"))), str(Decimal(output_price).quantize(Decimal("0.0001"))))


def _pricing_items(*items: dict) -> str:
    return json.dumps(list(items), ensure_ascii=False)


OFFICIAL_MODEL_CATALOG: dict[str, dict] = {
    "qwen-plus": {
        "display_name": "Qwen3.5-Plus",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "text",
        "capability_type": "chat",
        "support_features": "文本生成,深度思考,视觉理解",
        "tags": "文本生成,深度思考,视觉理解",
        "billing_mode": "token",
        "input_price_per_million": Decimal("0.8000"),
        "output_price_per_million": Decimal("4.8000"),
        "pricing_items": _pricing_items(
            {"label": "输入", "unit": "元/百万Token", "price": "0.8"},
            {"label": "输出", "unit": "元/百万Token", "price": "4.8"},
        ),
        "price_source": "official_doc",
        "description": "Qwen3.5原生视觉语言系列Plus模型，兼具文本生成、深度思考与视觉理解能力。",
        "hero_description": "Qwen3.5原生视觉语言系列Plus模型，基于混合架构设计，融合线性注意力与稀疏混合专家机制，在纯文本与多模态场景均具备高质量表现。",
    },
    "qwen-flash": {
        "display_name": "Qwen3.5-Flash",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "text",
        "capability_type": "chat",
        "support_features": "文本生成,深度思考,视觉理解",
        "tags": "文本生成,深度思考,视觉理解",
        "billing_mode": "token",
        "input_price_per_million": Decimal("0.2000"),
        "output_price_per_million": Decimal("2.0000"),
        "pricing_items": _pricing_items(
            {"label": "输入", "unit": "元/百万Token", "price": "0.2"},
            {"label": "输出", "unit": "元/百万Token", "price": "2"},
        ),
        "price_source": "official_doc",
        "description": "Qwen3.5原生视觉语言系列Flash模型，响应更快、成本更低。",
        "hero_description": "Qwen3.5原生视觉语言系列Flash模型，具备更高的推理效率，适合低延迟、高性价比的文本与多模态场景。",
    },
    "qwen-image-2.0": {
        "display_name": "Qwen-Image-2.0",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "image",
        "capability_type": "image",
        "support_features": "图片生成,图片编辑",
        "tags": "图片生成,图片编辑",
        "billing_mode": "per_image",
        "input_price_per_million": Decimal("0.0000"),
        "output_price_per_million": Decimal("0.0000"),
        "pricing_items": _pricing_items(
            {"label": "图片生成/编辑", "unit": "元/张", "price": "0.2"},
        ),
        "price_source": "official_doc",
        "description": "Qwen-Image-2.0系列加速版模型，实现图片生成与编辑融合。",
        "hero_description": "Qwen-Image-2.0系列加速版模型，具备更专业的文字渲染能力、更细腻的真实质感和更强的语义遵循能力。",
    },
    "qwen-image-2.0-pro": {
        "display_name": "Qwen-Image-2.0-Pro",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "image",
        "capability_type": "image",
        "support_features": "图片生成,图片编辑",
        "tags": "图片生成,图片编辑,高质量",
        "billing_mode": "per_image",
        "input_price_per_million": Decimal("0.0000"),
        "output_price_per_million": Decimal("0.0000"),
        "pricing_items": _pricing_items(
            {"label": "图片生成/编辑", "unit": "元/张", "price": "0.5"},
        ),
        "price_source": "official_doc",
        "description": "Qwen-Image-2.0系列满血版模型，具备更强文字渲染与真实质感。",
        "hero_description": "Qwen-Image-2.0系列满血版模型，适合商业级视觉内容生成与高质量图像编辑场景。",
    },
    "wan2.6-i2v-flash": {
        "display_name": "Wan2.6-I2V-Flash",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "video",
        "capability_type": "video",
        "support_features": "视频生成,多镜头叙事,音视频生成",
        "tags": "视频生成,多镜头,音视频",
        "billing_mode": "per_second",
        "input_price_per_million": Decimal("0.0000"),
        "output_price_per_million": Decimal("0.0000"),
        "pricing_items": _pricing_items(
            {"label": "720P 无声", "unit": "元/每秒", "price": "0.15"},
            {"label": "1080P 无声", "unit": "元/每秒", "price": "0.25"},
            {"label": "720P 有声", "unit": "元/每秒", "price": "0.3"},
            {"label": "1080P 有声", "unit": "元/每秒", "price": "0.5"},
        ),
        "price_source": "official_doc",
        "description": "万相2.6图生视频Flash模型，主打更快生成与更高性价比。",
        "hero_description": "万相2.6图生视频Flash模型，支持智能分镜调度、多镜头叙事和最高15秒的视频生成。",
    },
    "deepseek-v3.2": {
        "display_name": "DeepSeek-V3.2",
        "vendor_display_name": "DeepSeek",
        "provider": "alibaba-bailian",
        "category": "text",
        "capability_type": "chat",
        "support_features": "深度思考,文本生成",
        "tags": "深度思考,文本生成",
        "billing_mode": "token",
        "input_price_per_million": Decimal("2.0000"),
        "output_price_per_million": Decimal("3.0000"),
        "pricing_items": _pricing_items(
            {"label": "输入", "unit": "元/百万Token", "price": "2"},
            {"label": "输出", "unit": "元/百万Token", "price": "3"},
        ),
        "price_source": "official_doc",
        "description": "DeepSeek-V3.2 支持思考模式与非思考模式的工具调用。",
        "hero_description": "DeepSeek-V3.2 是引入稀疏注意力机制的正式版模型，同时支持深度思考与文本生成场景。",
    },
    "kimi-k2.5": {
        "display_name": "Kimi-K2.5",
        "vendor_display_name": "月之暗面",
        "provider": "alibaba-bailian",
        "category": "text",
        "capability_type": "chat",
        "support_features": "深度思考,视觉理解,文本生成",
        "tags": "深度思考,视觉理解,文本生成",
        "billing_mode": "token",
        "input_price_per_million": Decimal("4.0000"),
        "output_price_per_million": Decimal("21.0000"),
        "pricing_items": _pricing_items(
            {"label": "输入", "unit": "元/百万Token", "price": "4"},
            {"label": "输出", "unit": "元/百万Token", "price": "21"},
        ),
        "price_source": "official_doc",
        "description": "Kimi-K2.5 是原生多模态架构设计的全能模型。",
        "hero_description": "Kimi-K2.5 同时支持视觉与文本输入、思考与非思考模式、对话与 Agent 任务。",
    },
    "glm-5": {
        "display_name": "GLM-5",
        "vendor_display_name": "智谱",
        "provider": "alibaba-bailian",
        "category": "text",
        "capability_type": "chat",
        "support_features": "文本生成",
        "tags": "文本生成,工程生成",
        "billing_mode": "token",
        "input_price_per_million": Decimal("4.0000"),
        "output_price_per_million": Decimal("18.0000"),
        "pricing_items": _pricing_items(
            {"label": "输入", "unit": "元/百万Token", "price": "4"},
            {"label": "输出", "unit": "元/百万Token", "price": "18"},
        ),
        "price_source": "official_doc",
        "description": "GLM-5 面向 Coding 与 Agent 场景。",
        "hero_description": "GLM-5 在复杂系统工程与长程任务中具备强编码与工程生成能力。",
    },
    "minimax-m2.5": {
        "display_name": "MiniMax-M2.5",
        "vendor_display_name": "MiniMax",
        "provider": "alibaba-bailian",
        "category": "text",
        "capability_type": "chat",
        "support_features": "文本生成,深度思考",
        "tags": "文本生成,深度思考",
        "billing_mode": "token",
        "input_price_per_million": Decimal("2.1000"),
        "output_price_per_million": Decimal("8.4000"),
        "pricing_items": _pricing_items(
            {"label": "输入", "unit": "元/百万Token", "price": "2.1"},
            {"label": "输出", "unit": "元/百万Token", "price": "8.4"},
        ),
        "price_source": "official_doc",
        "description": "MiniMax-M2.5 是 MiniMax 推出的旗舰级开源大模型。",
        "hero_description": "MiniMax-M2.5 在编程、工具调用、搜索和办公等生产力场景达到行业领先水平。",
    },
    "qwen3-asr-flash": {
        "display_name": "Qwen3-ASR-Flash",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "audio",
        "capability_type": "audio",
        "support_features": "语言识别",
        "tags": "语音识别,多语种",
        "billing_mode": "per_second",
        "input_price_per_million": Decimal("0.0000"),
        "output_price_per_million": Decimal("0.0000"),
        "pricing_items": _pricing_items(
            {"label": "语音识别", "unit": "元/每秒", "price": "0.00022"},
        ),
        "price_source": "official_doc",
        "description": "Qwen3-ASR-Flash 是高精度、多语种语音识别模型。",
        "hero_description": "Qwen3-ASR-Flash 依托大模型与海量音频训练数据，在复杂环境下也能保持高精度转录。",
    },
    "qwen3-tts-vd-2026-01-26": {
        "display_name": "Qwen3-TTS-VD",
        "vendor_display_name": "Alibaba",
        "provider": "alibaba-bailian",
        "category": "audio",
        "capability_type": "audio",
        "support_features": "语音合成",
        "tags": "语音合成,多语种",
        "billing_mode": "per_10k_chars",
        "input_price_per_million": Decimal("0.0000"),
        "output_price_per_million": Decimal("0.0000"),
        "pricing_items": _pricing_items(
            {"label": "语音合成", "unit": "元/每万字符", "price": "0.8"},
        ),
        "price_source": "official_doc",
        "description": "Qwen3-TTS-VD 是实时语音合成大模型。",
        "hero_description": "Qwen3-TTS-VD 支持高保真实时语音合成，同一音色支持 11 个语种输出。",
    },
}


OFFICIAL_MODEL_ALIASES = {
    "qwen3.5-plus": "qwen-plus",
    "qwen3.5-flash": "qwen-flash",
    "qwen-image-2.0": "qwen-image-2.0",
    "qwen-image-2.0-pro": "qwen-image-2.0-pro",
    "wan2.6-i2v-flash": "wan2.6-i2v-flash",
    "deepseek-v3.2": "deepseek-v3.2",
    "kimi-k2.5": "kimi-k2.5",
    "glm-5": "glm-5",
    "minimax-m2.5": "minimax-m2.5",
    "qwen3-asr-flash": "qwen3-asr-flash",
    "qwen3-tts-vd-2026-01-26": "qwen3-tts-vd-2026-01-26",
}


def resolve_official_model_key(model_id: str) -> str | None:
    normalized = (model_id or "").strip().lower()
    normalized = normalized.split("/", 1)[-1]
    return OFFICIAL_MODEL_ALIASES.get(normalized, normalized if normalized in OFFICIAL_MODEL_CATALOG else None)


def get_official_model_metadata(model_id: str) -> dict | None:
    key = resolve_official_model_key(model_id)
    if not key:
        return None
    return OFFICIAL_MODEL_CATALOG.get(key)
