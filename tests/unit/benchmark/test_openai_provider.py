import pytest

from mcplint.benchmark.providers.openai_provider import OpenAIProvider
from mcplint.models.contracts import ToolAnnotation, ToolContract


def _tool(name: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


@pytest.mark.asyncio
async def test_openai_provider_raises_not_implemented() -> None:
    provider = OpenAIProvider(model="gpt-5")
    assert provider.name == "openai"
    with pytest.raises(NotImplementedError):
        await provider.run("Retrieve customer 1042.", [_tool("get_customer")])
