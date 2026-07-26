"""A deterministic, no-network provider used by scorer tests and offline demos."""

from __future__ import annotations

from collections.abc import Callable

from mcplint.benchmark.providers.base import ProviderResult
from mcplint.models.contracts import ToolContract


class FakeProvider:
    """Wraps a plain Python function so tests never need real API calls."""

    def __init__(
        self,
        model: str,
        responder: Callable[[str, list[ToolContract]], ProviderResult],
        *,
        name: str = "fake",
    ) -> None:
        self.name = name
        self.model = model
        self._responder = responder

    async def run(self, prompt: str, tools: list[ToolContract]) -> ProviderResult:
        return self._responder(prompt, tools)
