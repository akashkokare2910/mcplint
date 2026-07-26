"""Registry of all built-in rule classes."""

from __future__ import annotations

from mcplint.core.rules.ambiguity_rules import AmbiguousToolOverlapRule, MissingToolDistinctionRule
from mcplint.core.rules.base import Rule
from mcplint.core.rules.completeness_rules import (
    ExcessiveDescriptionLengthRule,
    MissingReturnSemanticsRule,
    UndefinedDomainTermRule,
    UndocumentedErrorBehaviourRule,
    UndocumentedRequiredConstraintRule,
)
from mcplint.core.rules.description_rules import (
    DescriptionRepeatsNameRule,
    MissingToolDescriptionRule,
    VagueToolDescriptionRule,
)
from mcplint.core.rules.safety_rules import (
    DestructiveToolWithoutWarningRule,
    StateChangingToolMarkedReadOnlyRule,
    ToolNameActionConflictRule,
)
from mcplint.core.rules.schema_rules import (
    MissingParameterDescriptionRule,
    SchemaDescriptionTypeConflictRule,
)

BUILTIN_RULES: list[type[Rule]] = [
    MissingToolDescriptionRule,
    DescriptionRepeatsNameRule,
    VagueToolDescriptionRule,
    MissingParameterDescriptionRule,
    MissingReturnSemanticsRule,
    UndocumentedErrorBehaviourRule,
    UndocumentedRequiredConstraintRule,
    SchemaDescriptionTypeConflictRule,
    ToolNameActionConflictRule,
    DestructiveToolWithoutWarningRule,
    StateChangingToolMarkedReadOnlyRule,
    AmbiguousToolOverlapRule,
    MissingToolDistinctionRule,
    ExcessiveDescriptionLengthRule,
    UndefinedDomainTermRule,
]
