"""Provider interface every benchmark backend (fake, Anthropic, OpenAI) implements."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from mcplint.models.contracts import ToolContract


class ProviderResult(BaseModel):
    tool: str | None
    arguments: dict[str, object] = Field(default_factory=dict)
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    error: str | None = None


class ToolCallingProvider(Protocol):
    name: str
    model: str

    async def run(self, prompt: str, tools: list[ToolContract]) -> ProviderResult: ...
