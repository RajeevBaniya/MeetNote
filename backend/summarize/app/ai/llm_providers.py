from typing import Dict, Protocol, Type


class LLMProvider(Protocol):
    def __init__(self, api_key: str, model_name: str) -> None:
        ...

    async def generate_content(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> str:
        ...


_llm_registry: Dict[str, Type[LLMProvider]] = {}


def register_llm_provider(name: str, provider_cls: Type[LLMProvider]) -> None:
    _llm_registry[name.strip().lower()] = provider_cls


def get_llm_provider_class(name: str) -> Type[LLMProvider]:
    name_clean = name.strip().lower()
    if name_clean not in _llm_registry:
        raise ValueError(f"LLM Provider '{name}' is not registered.")
    return _llm_registry[name_clean]
