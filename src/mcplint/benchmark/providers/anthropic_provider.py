"""Anthropic ToolCallingProvider adapter.

Requires the `anthropic` extra: `pip install "mcplint[anthropic]"`. The
`anthropic` package is imported lazily in `__init__` so importing this
module (or the rest of mcplint) never requires it to be installed.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from mcplint.benchmark.providers.base import ProviderResult
from mcplint.models.contracts import ToolContract

if TYPE_CHECKING:
    import anthropic

# Illustrative only: not authoritative pricing. USD per 1M tokens.
_PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-5": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.8, 4.0),
}


class AnthropicProvider:
    def __init__(self, model: str, *, api_key: str | None = None, max_tokens: int = 1024) -> None:
        try:
            import anthropic as anthropic_module
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for --provider anthropic. "
                'Install it with: pip install "mcplint[anthropic]"'
            ) from exc

        self.name = "anthropic"
        self.model = model
        self.max_tokens = max_tokens
        self.client: anthropic.AsyncAnthropic = anthropic_module.AsyncAnthropic(api_key=api_key)

    async def run(self, prompt: str, tools: list[ToolContract]) -> ProviderResult:
        anthropic_tools: list[dict[str, Any]] = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.input_schema,
            }
            for tool in tools
        ]

        start = time.monotonic()
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=anthropic_tools,  # type: ignore[arg-type]
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a scored trial error, not a crash
            latency_ms = (time.monotonic() - start) * 1000
            return ProviderResult(tool=None, latency_ms=latency_ms, error=str(exc))

        latency_ms = (time.monotonic() - start) * 1000
        tool_use = next((block for block in message.content if block.type == "tool_use"), None)
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        if tool_use is None:
            return ProviderResult(
                tool=None,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=self._estimate_cost(input_tokens, output_tokens),
            )

        return ProviderResult(
            tool=tool_use.name,
            arguments=dict(tool_use.input),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=self._estimate_cost(input_tokens, output_tokens),
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float | None:
        pricing = _PRICING_PER_MILLION_TOKENS.get(self.model)
        if pricing is None:
            return None
        input_price, output_price = pricing
        return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
