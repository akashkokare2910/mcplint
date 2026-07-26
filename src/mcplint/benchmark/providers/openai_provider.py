"""OpenAI ToolCallingProvider adapter.

TODO(Phase 5 follow-up): implement against the OpenAI Responses/Chat
Completions tool-calling API, mirroring AnthropicProvider. Structured as a
separate adapter per spec so it does not block the Anthropic implementation.
Requires the `openai` extra: `pip install "mcplint[openai]"`.
"""

from __future__ import annotations

from mcplint.benchmark.providers.base import ProviderResult
from mcplint.models.contracts import ToolContract


class OpenAIProvider:
    def __init__(self, model: str, *, api_key: str | None = None) -> None:
        self.name = "openai"
        self.model = model
        self.api_key = api_key

    async def run(self, prompt: str, tools: list[ToolContract]) -> ProviderResult:
        raise NotImplementedError(
            "OpenAI provider is not implemented yet. Use --provider anthropic or "
            "--provider fake. Tracked in IMPLEMENTATION_STATUS.md."
        )
