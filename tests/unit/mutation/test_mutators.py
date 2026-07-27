from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.mutation.mutators import (
    MUTATORS,
    StripDestructiveWarningMutator,
    StripDistinctionLanguageMutator,
    TruncateToVagueMutator,
)


def _tool(description: str | None, destructive: bool = False) -> ToolContract:
    return ToolContract(
        id="a",
        name="delete_customer",
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(destructive_hint=destructive),
        raw={},
    )


def test_strip_destructive_warning_applies_only_to_destructive_tools_with_warning() -> None:
    mutator = StripDestructiveWarningMutator()
    warned = _tool(
        "Deletes a customer. This action is permanent and cannot be undone.", destructive=True
    )
    unwarned = _tool("Deletes a customer.", destructive=True)
    not_destructive = _tool(
        "Deletes a customer. This action is permanent and cannot be undone.", destructive=False
    )
    assert mutator.applies_to(warned) is True
    assert mutator.applies_to(unwarned) is False
    assert mutator.applies_to(not_destructive) is False


def test_strip_destructive_warning_removes_only_the_warning_sentence() -> None:
    mutator = StripDestructiveWarningMutator()
    tool = _tool(
        "Deletes a customer record. This action is permanent and cannot be undone.",
        destructive=True,
    )
    mutated = mutator.mutate(tool)
    assert mutated.description == "Deletes a customer record."
    # the original is untouched (pure function)
    assert (
        tool.description
        == "Deletes a customer record. This action is permanent and cannot be undone."
    )


def test_strip_distinction_language_removes_matching_sentence() -> None:
    mutator = StripDistinctionLanguageMutator()
    tool = _tool("Retrieve a customer by its exact ID. Use search_customers otherwise.")
    assert mutator.applies_to(tool) is True
    mutated = mutator.mutate(tool)
    assert "exact" not in mutated.description.lower()
    assert "Use search_customers otherwise." in mutated.description


def test_strip_distinction_language_does_not_apply_without_keywords() -> None:
    mutator = StripDistinctionLanguageMutator()
    tool = _tool("Retrieve a customer record.")
    assert mutator.applies_to(tool) is False


def test_truncate_to_vague_shortens_long_description() -> None:
    mutator = TruncateToVagueMutator()
    tool = _tool("Retrieve a customer record by its exact customer identifier.")
    assert mutator.applies_to(tool) is True
    mutated = mutator.mutate(tool)
    assert mutated.description == "Retrieve a"


def test_truncate_to_vague_does_not_apply_to_already_short_description() -> None:
    mutator = TruncateToVagueMutator()
    tool = _tool("Gets data.")
    assert mutator.applies_to(tool) is False


def test_mutators_do_not_apply_to_missing_description() -> None:
    tool = _tool(None)
    for mutator_cls in MUTATORS:
        assert mutator_cls().applies_to(tool) is False
