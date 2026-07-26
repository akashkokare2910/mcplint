from mcplint.models.fixes import RewriteSuggestion
from mcplint.reporters.fix_markdown import render_fix_markdown


def test_render_fix_markdown_no_suggestions() -> None:
    output = render_fix_markdown("customer-server", [])
    assert "No actionable suggestions" in output


def test_render_fix_markdown_lists_suggestions() -> None:
    suggestion = RewriteSuggestion(
        tool_name="delete_customer",
        proposed_description="Deletes a customer. This action is permanent and cannot be undone.",
        resolved_rule_ids=["destructive-tool-without-warning"],
        explanation="Added a destructive-operation warning.",
        confidence=0.9,
    )
    output = render_fix_markdown("customer-server", [suggestion])
    assert "delete_customer" in output
    assert "destructive-tool-without-warning" in output
    assert "cannot be undone" in output
    assert "never overwrites source files" in output
