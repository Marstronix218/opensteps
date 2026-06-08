import pytest

from app.services.policies import PolicyEngine

POLICY = """\
default: deny
rules:
  - effect: allow
    agent: code-*
    tool: github
    actions: [create_*]
    resources: [repo:example/*]
  - effect: approval_required
    agent: code-agent
    tool: github
    actions: [merge_pull_request]
    resources: ["*"]
"""


@pytest.mark.parametrize(
    ("agent", "tool", "action", "resource", "expected"),
    [
        ("code-agent", "github", "create_pull_request", "repo:example/app", "allowed"),
        ("code-agent", "github", "merge_pull_request", "repo:example/app", "approval_required"),
        ("code-agent", "aws", "delete_instance", "instance:123", "denied"),
    ],
)
def test_policy_decisions(
    agent: str, tool: str, action: str, resource: str, expected: str
) -> None:
    result = PolicyEngine().evaluate_document(
        POLICY, agent=agent, tool=tool, action=action, resource=resource
    )
    assert result.decision == expected

