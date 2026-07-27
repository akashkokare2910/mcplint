"""Resolves a --provider/--model CLI selection to a ToolCallingProvider instance.

"fake" and "anthropic" are implemented. "openai" is a typed stub: see
`openai_provider.py`: that raises NotImplementedError only when actually
invoked, per the spec's "don't let OpenAI delay Anthropic" guidance.
"""

from __future__ import annotations

from mcplint.benchmark.providers.base import ProviderResult, ToolCallingProvider
from mcplint.benchmark.providers.fake import FakeProvider
from mcplint.models.contracts import ToolContract

SUPPORTED_PROVIDERS = ("fake", "anthropic", "openai")


class ProviderNotAvailableError(Exception):
    """Raised when a requested provider isn't implemented yet or misconfigured."""


def _echo_first_tool(prompt: str, tools: list[ToolContract]) -> ProviderResult:
    if not tools:
        return ProviderResult(tool=None, error="no tools available")
    return ProviderResult(tool=tools[0].name, arguments={})


def create_provider(provider: str, model: str | None) -> ToolCallingProvider:
    if provider == "fake":
        return FakeProvider(model=model or "fake-echo-model", responder=_echo_first_tool)

    if provider == "anthropic":
        if model is None:
            raise ProviderNotAvailableError(
                "--model is required for --provider anthropic (e.g. claude-sonnet-5)."
            )
        try:
            from mcplint.benchmark.providers.anthropic_provider import AnthropicProvider
        except ImportError as exc:
            raise ProviderNotAvailableError(str(exc)) from exc
        return AnthropicProvider(model=model)

    if provider == "openai":
        from mcplint.benchmark.providers.openai_provider import OpenAIProvider

        if model is None:
            raise ProviderNotAvailableError("--model is required for --provider openai.")
        return OpenAIProvider(model=model)

    raise ProviderNotAvailableError(
        f"Unknown provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
    )
