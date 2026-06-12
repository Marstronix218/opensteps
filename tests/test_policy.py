import pytest

from opensteps.policy import Policy, PolicyError

FULL_POLICY = """
version: "0.1"
default: deny
rules:
  - id: allow-reads
    tool: "read_*"
    action: allow
  - id: payments-small-approved-payee
    tool: create_payment
    where:
      - param: payee
        one_of: ["Acme", "CloudHost"]
      - param: amount
        max: 5000
    action: allow
  - id: payments-need-approval
    tool: create_payment
    where:
      - param: amount
        max: 10000
    action: approve
  - id: deny-payments
    tool: create_payment
    action: deny
  - id: scoped-server
    server: "books-*"
    tool: post_entry
    action: allow
  - id: regex-memo
    tool: tag_entry
    where:
      - param: memo
        matches: "Q[1-4]-\\\\d{4}"
    action: allow
"""


@pytest.fixture
def policy(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(FULL_POLICY)
    return Policy.load(path)


def test_glob_tool_match(policy):
    assert policy.evaluate("s", "read_invoice", {}).rule_id == "allow-reads"
    assert policy.evaluate("s", "read_anything", {}).action == "allow"


def test_first_match_wins(policy):
    d = policy.evaluate("s", "create_payment", {"payee": "Acme", "amount": 100})
    assert (d.action, d.rule_id) == ("allow", "payments-small-approved-payee")


def test_where_condition_falls_through_to_next_rule(policy):
    # Unknown payee but under 10000 -> approval rule
    d = policy.evaluate("s", "create_payment", {"payee": "Globex", "amount": 8000})
    assert (d.action, d.rule_id) == ("approve", "payments-need-approval")
    # Over every threshold -> explicit deny rule
    d = policy.evaluate("s", "create_payment", {"payee": "Globex", "amount": 45000})
    assert (d.action, d.rule_id) == ("deny", "deny-payments")


def test_missing_param_fails_condition(policy):
    d = policy.evaluate("s", "create_payment", {"payee": "Acme"})
    assert d.rule_id == "deny-payments"


def test_default_applies_when_nothing_matches(policy):
    d = policy.evaluate("s", "unknown_tool", {})
    assert (d.action, d.rule_id) == ("deny", "default")


def test_server_glob(policy):
    assert policy.evaluate("books-prod", "post_entry", {}).action == "allow"
    assert policy.evaluate("crm", "post_entry", {}).rule_id == "default"


def test_regex_fullmatch(policy):
    assert policy.evaluate("s", "tag_entry", {"memo": "Q3-2026"}).action == "allow"
    assert policy.evaluate("s", "tag_entry", {"memo": "xQ3-2026x"}).rule_id == "default"


def test_numeric_condition_rejects_bool(policy):
    # True == 1 in Python; a bool must not satisfy a numeric bound
    d = policy.evaluate("s", "create_payment", {"payee": "Acme", "amount": True})
    assert d.rule_id == "deny-payments"


def write_and_load(tmp_path, text):
    path = tmp_path / "p.yaml"
    path.write_text(text)
    return Policy.load(path)


def test_default_allow_supported(tmp_path):
    p = write_and_load(tmp_path, 'version: "0.1"\ndefault: allow\nrules: []\n')
    assert p.evaluate("s", "anything", {}).action == "allow"


@pytest.mark.parametrize(
    "bad",
    [
        'version: "0.1"\ndefault: maybe\nrules: []\n',
        'version: "0.1"\ndefault: deny\nrules:\n  - id: x\n    tool: t\n    action: explode\n',
        'version: "0.1"\ndefault: deny\nrules:\n  - tool: t\n    action: allow\n',
        'version: "0.1"\ndefault: deny\nrules:\n  - id: dup\n    tool: a\n    action: allow\n  - id: dup\n    tool: b\n    action: deny\n',
        'version: "0.1"\ndefault: deny\nrules:\n  - id: x\n    tool: t\n    action: allow\n    where:\n      - param: p\n        sideways: 1\n',
    ],
)
def test_invalid_policies_raise(tmp_path, bad):
    with pytest.raises(PolicyError):
        write_and_load(tmp_path, bad)
