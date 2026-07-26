import pytest

from mcplint.benchmark.providers.factory import ProviderNotAvailableError, create_provider
from mcplint.benchmark.providers.openai_provider import OpenAIProvider


def test_create_provider_fake_defaults_model() -> None:
    provider = create_provider("fake", None)
    assert provider.name == "fake"
    assert provider.model == "fake-echo-model"


def test_create_provider_anthropic_requires_model() -> None:
    with pytest.raises(ProviderNotAvailableError, match="--model is required"):
        create_provider("anthropic", None)


def test_create_provider_anthropic_returns_adapter() -> None:
    pytest.importorskip("anthropic", reason="requires the optional 'anthropic' extra")
    from mcplint.benchmark.providers.anthropic_provider import AnthropicProvider

    provider = create_provider("anthropic", "claude-sonnet-5")
    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-sonnet-5"


def test_create_provider_openai_returns_stub_adapter() -> None:
    provider = create_provider("openai", "gpt-5")
    assert isinstance(provider, OpenAIProvider)


def test_create_provider_unknown_raises() -> None:
    with pytest.raises(ProviderNotAvailableError, match="Unknown provider"):
        create_provider("not-a-real-provider", None)
