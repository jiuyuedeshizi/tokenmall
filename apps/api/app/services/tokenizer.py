from __future__ import annotations

import json

import tiktoken


DEFAULT_ENCODING = "cl100k_base"
CHAT_MESSAGE_OVERHEAD = 4
CHAT_REPLY_PRIMER = 2


def get_encoding():
    return tiktoken.get_encoding(DEFAULT_ENCODING)


def count_text_tokens(text: str) -> int:
    if not text:
        return 0
    encoding = get_encoding()
    return len(encoding.encode(text))


def normalize_message_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def estimate_chat_messages_tokens(messages: list[dict]) -> int:
    encoding = get_encoding()
    token_count = 0
    for message in messages:
        token_count += CHAT_MESSAGE_OVERHEAD
        token_count += len(encoding.encode(str(message.get("role", ""))))
        token_count += len(encoding.encode(normalize_message_content(message.get("content", ""))))
        name = message.get("name")
        if name:
            token_count += len(encoding.encode(str(name)))
    token_count += CHAT_REPLY_PRIMER
    return max(token_count, 1)
