"""Cross-tool semantic ambiguity engine.

Computes a 0-1 ambiguity score between every pair of tools from normalised
token overlap, name similarity, description similarity, and input-schema
(parameter name) similarity, plus optional sentence-transformer embeddings
when the `semantic` extra is installed. Every flagged pair carries structured
evidence (shared verbs/entities/parameters, absent distinctions) so the
result is inspectable rather than an opaque score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mcplint.core.rules.safety_rules import READ_VERBS, WRITE_VERBS, first_word
from mcplint.models.contracts import ToolContract

DEFAULT_AMBIGUITY_THRESHOLD = 0.55

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "for",
        "to",
        "and",
        "or",
        "in",
        "on",
        "by",
        "with",
        "is",
        "are",
        "this",
        "that",
        "it",
        "its",
        "your",
        "you",
        "from",
        "as",
        "at",
        "be",
        "will",
        "if",
        "not",
        "can",
        "does",
        "do",
    }
)
_MANY_HINTS = frozenset({"list", "search", "find", "query"})
_ONE_HINTS = frozenset({"get", "fetch", "show", "view"})


def _tokens(text: str, *, drop_stopwords: bool) -> set[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    words = [w for w in cleaned.split() if w]
    if drop_stopwords:
        words = [w for w in words if w not in _STOPWORDS]
    return set(words)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


@dataclass(frozen=True)
class AmbiguityEvidence:
    shared_verbs: tuple[str, ...] = ()
    shared_entities: tuple[str, ...] = ()
    overlapping_parameters: tuple[str, ...] = ()
    absent_exact_vs_search_distinction: bool = False
    absent_one_vs_many_distinction: bool = False
    absent_read_vs_write_distinction: bool = False


@dataclass(frozen=True)
class AmbiguityPairResult:
    tool_a: str
    tool_b: str
    score: float
    name_similarity: float
    description_similarity: float
    schema_similarity: float
    evidence: AmbiguityEvidence = field(default_factory=AmbiguityEvidence)

    def has_missing_distinction(self) -> bool:
        return (
            self.evidence.absent_exact_vs_search_distinction
            or self.evidence.absent_one_vs_many_distinction
            or self.evidence.absent_read_vs_write_distinction
        )


def compute_ambiguity(tool_a: ToolContract, tool_b: ToolContract) -> AmbiguityPairResult:
    name_tokens_a = _tokens(tool_a.name.replace("_", " ").replace("-", " "), drop_stopwords=False)
    name_tokens_b = _tokens(tool_b.name.replace("_", " ").replace("-", " "), drop_stopwords=False)
    name_similarity = _jaccard(name_tokens_a, name_tokens_b)

    desc_tokens_a = _tokens(tool_a.description or "", drop_stopwords=True)
    desc_tokens_b = _tokens(tool_b.description or "", drop_stopwords=True)
    description_similarity = _jaccard(desc_tokens_a, desc_tokens_b)

    schema_similarity = _jaccard(tool_a.parameter_names(), tool_b.parameter_names())

    score = 0.25 * name_similarity + 0.45 * description_similarity + 0.30 * schema_similarity

    verb_a, verb_b = first_word(tool_a.name), first_word(tool_b.name)
    action_verbs = READ_VERBS | WRITE_VERBS
    shared_verbs = tuple(sorted({verb_a} & {verb_b} & action_verbs))
    shared_entities = tuple(sorted((name_tokens_a & name_tokens_b) - action_verbs))
    overlapping_parameters = tuple(sorted(tool_a.parameter_names() & tool_b.parameter_names()))

    combined_description = f"{tool_a.description or ''} {tool_b.description or ''}".lower()

    absent_exact_vs_search = (
        {verb_a, verb_b} & _ONE_HINTS
        and {verb_a, verb_b} & _MANY_HINTS
        and "exact" not in combined_description
    )
    one_vs_many_keywords = ("single", "one or more", "list of", "multiple")
    absent_one_vs_many = (
        bool({verb_a, verb_b} & _ONE_HINTS)
        and bool({verb_a, verb_b} & _MANY_HINTS)
        and not any(kw in combined_description for kw in one_vs_many_keywords)
    )
    read_only_a = bool(tool_a.annotations.read_only_hint)
    read_only_b = bool(tool_b.annotations.read_only_hint)
    absent_read_vs_write = read_only_a != read_only_b and "read-only" not in combined_description

    evidence = AmbiguityEvidence(
        shared_verbs=shared_verbs,
        shared_entities=shared_entities,
        overlapping_parameters=overlapping_parameters,
        absent_exact_vs_search_distinction=bool(absent_exact_vs_search),
        absent_one_vs_many_distinction=bool(absent_one_vs_many),
        absent_read_vs_write_distinction=absent_read_vs_write,
    )

    return AmbiguityPairResult(
        tool_a=tool_a.name,
        tool_b=tool_b.name,
        score=round(score, 4),
        name_similarity=round(name_similarity, 4),
        description_similarity=round(description_similarity, 4),
        schema_similarity=round(schema_similarity, 4),
        evidence=evidence,
    )
