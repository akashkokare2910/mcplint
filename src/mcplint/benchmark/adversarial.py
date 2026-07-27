"""Generates adversarial BenchmarkCase entries directly from a BehavioralContract.

The output is a plain `BenchmarkDataset`, identical in shape to a
hand-written `evals.yaml`, so it runs through the existing
`run_benchmark`/`scorer.py` machinery unchanged. Generation itself is
fully deterministic and template-based: no LLM key is needed to produce a
dataset, only to run one against a real model.

Each `prefer_over` entry in the contract states, in plain language, the
scenario under which one tool should be chosen over another. That is
already an adversarial test case: it deliberately targets the exact
ambiguity the contract exists to resolve. Two tools that both declare
`prefer_over` pointing at each other (with different `when` scenarios)
each contribute their own case; they are complementary, not duplicates.

`avoid_when` and `expected_failures` are not turned into cases here.
`BenchmarkCase.expected` requires a definite correct tool, and neither
field states one on its own. `expected_failures` also describes a runtime
failure mode, not a tool-selection choice, and the benchmark never
executes a tool for real (see `scorer.py`) so there is nothing to observe
a failure against yet.
"""

from __future__ import annotations

from mcplint.models.benchmark import BenchmarkCase, BenchmarkDataset, ExpectedToolCall
from mcplint.models.contract import BehavioralContract
from mcplint.models.snapshot import MCPServerSnapshot


def generate_adversarial_dataset(
    contract: BehavioralContract, snapshot: MCPServerSnapshot
) -> BenchmarkDataset:
    snapshot_tool_names = {tool.name for tool in snapshot.tools}
    cases: list[BenchmarkCase] = []

    for tool_name in sorted(contract.tools):
        if tool_name not in snapshot_tool_names:
            continue
        behavior = contract.tools[tool_name]

        for other_tool_name in sorted(behavior.prefer_over):
            if other_tool_name not in snapshot_tool_names:
                continue
            rule = behavior.prefer_over[other_tool_name]
            scenario = rule.when.strip().rstrip(".")
            prompt = f"{scenario}. Decide which tool to use: {tool_name} or {other_tool_name}."

            cases.append(
                BenchmarkCase(
                    id=f"prefer-{tool_name}-over-{other_tool_name}",
                    prompt=prompt,
                    expected=ExpectedToolCall(tool=tool_name, forbidden_tools=[other_tool_name]),
                )
            )

    return BenchmarkDataset(name=f"{contract.name}-adversarial", version="1", cases=cases)
