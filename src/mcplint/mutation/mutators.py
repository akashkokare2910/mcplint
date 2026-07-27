"""Pure ToolContract -> ToolContract mutators for contract mutation testing.

Each mutator deliberately reverses one thing a built-in rule checks for,
so a mutation that "survives" (does not measurably hurt benchmark
accuracy) points at a real gap between the deterministic linter and the
benchmark's actual sensitivity, not a hypothetical one.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import ClassVar

from mcplint.core.rules.safety_rules import DESTRUCTIVE_WARNING_HINTS
from mcplint.models.contracts import ToolContract

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_DISTINCTION_KEYWORDS = re.compile(
    r"\b(exact|single|one or more|list of|multiple|read-only|"
    r"already have|already know)\b",
    re.IGNORECASE,
)


def _drop_matching_sentences(description: str, pattern: re.Pattern[str]) -> str:
    sentences = _SENTENCE_SPLIT.split(description)
    kept = [sentence for sentence in sentences if not pattern.search(sentence)]
    return " ".join(kept).strip()


class Mutator(ABC):
    id: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def applies_to(self, tool: ToolContract) -> bool: ...

    @abstractmethod
    def mutate(self, tool: ToolContract) -> ToolContract: ...


class StripDestructiveWarningMutator(Mutator):
    id = "strip-destructive-warning"
    title = "Strip destructive-operation warning"
    description = (
        "Removes the sentence warning that a destructive action is permanent "
        "or irreversible, simulating the regression destructive-tool-without-warning "
        "exists to catch."
    )

    def applies_to(self, tool: ToolContract) -> bool:
        return bool(tool.annotations.destructive_hint) and bool(
            tool.description and DESTRUCTIVE_WARNING_HINTS.search(tool.description)
        )

    def mutate(self, tool: ToolContract) -> ToolContract:
        assert tool.description is not None
        new_description = _drop_matching_sentences(tool.description, DESTRUCTIVE_WARNING_HINTS)
        return tool.model_copy(update={"description": new_description})


class StripDistinctionLanguageMutator(Mutator):
    id = "strip-distinction-language"
    title = "Strip tool-distinction language"
    description = (
        "Removes sentences containing exact-vs-search, one-vs-many, or "
        "read-vs-write distinguishing language, simulating the regression "
        "missing-tool-distinction and ambiguous-tool-overlap exist to catch."
    )

    def applies_to(self, tool: ToolContract) -> bool:
        return bool(tool.description and _DISTINCTION_KEYWORDS.search(tool.description))

    def mutate(self, tool: ToolContract) -> ToolContract:
        assert tool.description is not None
        new_description = _drop_matching_sentences(tool.description, _DISTINCTION_KEYWORDS)
        return tool.model_copy(update={"description": new_description})


class TruncateToVagueMutator(Mutator):
    id = "truncate-to-vague"
    title = "Truncate description to vague"
    description = (
        "Truncates the description to two words, simulating the regression "
        "vague-tool-description exists to catch."
    )

    def applies_to(self, tool: ToolContract) -> bool:
        return bool(tool.description and len(tool.description.split()) > 3)

    def mutate(self, tool: ToolContract) -> ToolContract:
        assert tool.description is not None
        words = tool.description.split()[:2]
        return tool.model_copy(update={"description": " ".join(words)})


MUTATORS: list[type[Mutator]] = [
    StripDestructiveWarningMutator,
    StripDistinctionLanguageMutator,
    TruncateToVagueMutator,
]
