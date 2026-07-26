from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("anthropic", reason="requires the optional 'anthropic' extra")

from mcplint.benchmark.providers.anthropic_provider import AnthropicProvider  # noqa: E402
from mcplint.models.contracts import ToolAnnotation, ToolContract  # noqa: E402


def _tool(name: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def _fake_message(*, tool_use: bool) -> SimpleNamespace:
    content = (
        [SimpleNamespace(type="tool_use", name="get_customer", input={"customer_id": "1042"})]
        if tool_use
        else [SimpleNamespace(type="text", text="I need more information.")]
    )
    return SimpleNamespace(
        content=content, usage=SimpleNamespace(input_tokens=100, output_tokens=20)
    )


@pytest.mark.asyncio
async def test_anthropic_provider_maps_tool_use_block() -> None:
    provider = AnthropicProvider(model="claude-sonnet-5", api_key="sk-fake")
    provider.client.messages.create = AsyncMock(return_value=_fake_message(tool_use=True))

    result = await provider.run("Retrieve customer 1042.", [_tool("get_customer")])

    assert result.tool == "get_customer"
    assert result.arguments == {"customer_id": "1042"}
    assert result.input_tokens == 100
    assert result.output_tokens == 20
    assert result.estimated_cost is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_anthropic_provider_no_tool_use_returns_none_tool() -> None:
    provider = AnthropicProvider(model="claude-sonnet-5", api_key="sk-fake")
    provider.client.messages.create = AsyncMock(return_value=_fake_message(tool_use=False))

    result = await provider.run("Hello.", [_tool("get_customer")])

    assert result.tool is None
    assert result.error is None


@pytest.mark.asyncio
async def test_anthropic_provider_unknown_model_has_no_cost_estimate() -> None:
    provider = AnthropicProvider(model="some-future-model", api_key="sk-fake")
    provider.client.messages.create = AsyncMock(return_value=_fake_message(tool_use=True))

    result = await provider.run("Retrieve customer 1042.", [_tool("get_customer")])

    assert result.estimated_cost is None


@pytest.mark.asyncio
async def test_anthropic_provider_wraps_api_errors_as_provider_result() -> None:
    provider = AnthropicProvider(model="claude-sonnet-5", api_key="sk-fake")
    provider.client.messages.create = AsyncMock(side_effect=RuntimeError("rate limited"))

    result = await provider.run("Retrieve customer 1042.", [_tool("get_customer")])

    assert result.tool is None
    assert result.error == "rate limited"
