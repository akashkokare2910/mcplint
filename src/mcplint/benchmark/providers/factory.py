"""Resolves a --provider/--model CLI selection to a ToolCallingProvider instance.

Only "fake" is implemented in this phase — Anthropic/OpenAI adapters land in
Phase 5 (see IMPLEMENTATION_STATUS.md). Requesting them raises a clear,
typed error rather than silently falling back to a stub.
"""

from __future__ import annotations

from mcplint.benchmark.providers.base import ProviderResult, ToolCallingProvider
from mcplint.benchmark.providers.fake import FakeProvider
from mcplint.models.contracts import ToolContract

SUPPORTED_PROVIDERS = ("fake", "anthropic", "openai")


class ProviderNotAvailableError(Exception):
    """Raised when a requested provider isn't implemented yet."""


def _echo_first_tool(prompt: str, tools: list[ToolContract]) -> ProviderResult:
    if not tools:
        return ProviderResult(tool=None, error="no tools available")
    return ProviderResult(tool=tools[0].name, arguments={})


def create_provider(provider: str, model: str | None) -> ToolCallingProvider:
    if provider == "fake":
        return FakeProvider(model=model or "fake-echo-model", responder=_echo_first_tool)
    if provider in ("anthropic", "openai"):
        raise ProviderNotAvailableError(
            f"Provider '{provider}' is not implemented yet (Phase 5). "
            "Use --provider fake for a network-free dry run."
        )
    raise ProviderNotAvailableError(
        f"Unknown provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
    )
