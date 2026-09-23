"""Chat LLM access: provider-agnostic via langchain's init_chat_model.

Switching providers (openai, anthropic, ...) is a config change
(LLM_PROVIDER / LLM_MODEL), not a code change.

LLM_PROVIDER=litellm routes through the litellm proxy (see litellm/config.yaml
for the underlying provider/model each alias maps to) instead of calling a
provider directly.
"""

import json
import re

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from pi_core.config import Settings, get_settings

_PROVIDER_API_KEY_SETTING = {
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
}

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def get_chat_model(settings: Settings | None = None, *, temperature: float = 0.3) -> BaseChatModel:
    """Return a chat model configured from settings.llm_provider / settings.llm_model."""
    settings = settings or get_settings()
    provider = settings.llm_provider
    if provider == "litellm":
        return init_chat_model(
            model=settings.llm_model,
            model_provider="openai",
            base_url=settings.litellm_base_url,
            api_key=settings.litellm_master_key or "not-needed",
            temperature=temperature,
        )
    kwargs: dict = {}
    api_key_field = _PROVIDER_API_KEY_SETTING.get(provider)
    if api_key_field:
        api_key = getattr(settings, api_key_field, "")
        if api_key:
            kwargs["api_key"] = api_key
    return init_chat_model(
        model=settings.llm_model,
        model_provider=provider,
        temperature=temperature,
        **kwargs,
    )


def extract_json(text: str) -> dict:
    """Parse a JSON object out of an LLM response, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if "\n" in cleaned:
            cleaned = cleaned.split("\n", 1)[1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(cleaned)
        if not match:
            raise
        return json.loads(match.group(0))
