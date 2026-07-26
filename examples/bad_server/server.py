"""An intentionally bad example MCP server used to exercise every built-in rule.

Each tool below is a deliberate, minimal trigger for one or more rules. See
the comment above each tool for which rule(s) it exists to demonstrate.
Run directly: python examples/bad_server/server.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

mcp = FastMCP("bad-customer-server")


# missing-tool-description
@mcp.tool()
def ping() -> str:
    return "pong"


# description-repeats-name, vague-tool-description (both < 4 normalized words)
@mcp.tool(description="Get status")
def get_status() -> str:
    return "ok"


# vague-tool-description
@mcp.tool(description="Does stuff.")
def do_thing() -> str:
    return "done"


# missing-parameter-description, missing-return-semantics, undocumented-error-behaviour
@mcp.tool(description="Look up a record by its identifier in the internal store.")
def fetch_record(record_id: str) -> dict:
    return {"record_id": record_id}


# undocumented-required-constraint (enum values not mentioned in description)
@mcp.tool(description="List items filtered by category.")
def list_items(
    category: Annotated[
        Literal["electronics", "furniture", "clothing"],
        Field(description="The category to filter by."),
    ],
) -> list[str]:
    return []


# schema-description-type-conflict (numeric wording on a string-typed parameter)
@mcp.tool(description="Count records matching a limit.")
def count_records(
    limit: Annotated[str, Field(description="The number of records to return.")],
) -> int:
    return 0


# tool-name-action-conflict, destructive-tool-without-warning
@mcp.tool(
    description="Get the compliance report for an account.",
    annotations=ToolAnnotations(destructiveHint=True),
)
def get_report(account_id: str) -> dict[str, str]:
    return {"account_id": account_id}


# destructive-tool-without-warning
@mcp.tool(
    description="Deletes all records for a customer from the database.",
    annotations=ToolAnnotations(destructiveHint=True),
)
def delete_all_records(customer_id: str) -> bool:
    return True


# state-changing-tool-marked-read-only
@mcp.tool(
    description="Updates the notification settings for a customer.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
def update_settings(customer_id: str, enabled: bool) -> bool:
    return enabled


# ambiguous-tool-overlap, missing-tool-distinction (paired with find_widget below)
@mcp.tool(description="Retrieve a widget by its ID.")
def get_widget(widget_id: Annotated[str, Field(description="The widget ID.")]) -> dict[str, str]:
    return {"widget_id": widget_id}


# ambiguous-tool-overlap, missing-tool-distinction (paired with get_widget above)
@mcp.tool(description="Retrieve a widget by search criteria.")
def find_widget(widget_id: Annotated[str, Field(description="The widget ID.")]) -> dict[str, str]:
    return {"widget_id": widget_id}


# excessive-description-length
@mcp.tool(
    description=(
        "Summarizes a compliance report for a given account over a configurable "
        "time window, aggregating transaction history, risk flags, prior audit "
        "findings, related-party relationships, sanctions screening results, "
        "politically-exposed-person status, source-of-funds notes, beneficial "
        "ownership chains, historical name changes, address history, linked "
        "accounts across business units, previously filed suspicious activity "
        "reports, watchlist hits and their resolutions, know-your-customer "
        "refresh dates, risk rating history and rationale, relationship manager "
        "notes, and any open remediation items, then produces a single natural "
        "language narrative intended for a compliance analyst to review before "
        "an account periodic review meeting, including a recommended next "
        "action and a confidence indicator for that recommendation based on "
        "how complete the underlying records were at generation time, which "
        "may vary considerably between accounts depending on how long the "
        "relationship has existed and how many systems of record contributed "
        "data to this particular summary generation run."
    )
)
def summarize_report(account_id: str) -> str:
    return ""


# undefined-domain-term ("AUM" is not a well-known acronym and is not explained)
@mcp.tool(description="Look up an account's current AUM and risk tier.")
def lookup_account(account_id: str) -> dict[str, str]:
    return {"account_id": account_id}


if __name__ == "__main__":
    mcp.run()
