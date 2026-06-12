"""YAML policy engine: first-match-wins rules over tool calls.

A rule matches when its `tool` glob (and `server` glob, if given) match and
every `where` condition holds against the call arguments. A condition on a
missing parameter fails, so the rule falls through to the next one. If no
rule matches, the file-level `default` action applies with rule_id "default".
"""

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

ACTIONS = ("allow", "deny", "approve")
DEFAULT_ACTIONS = ("allow", "deny")
CONDITION_KEYS = ("equals", "one_of", "max", "min", "matches")


class PolicyError(Exception):
    pass


@dataclass
class Decision:
    action: str
    rule_id: str


def _condition_holds(cond: dict, arguments: dict) -> bool:
    param = cond["param"]
    if param not in arguments:
        return False
    value = arguments[param]

    if "equals" in cond:
        return value == cond["equals"]
    if "one_of" in cond:
        return value in cond["one_of"]
    if "max" in cond or "min" in cond:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if "max" in cond and value > cond["max"]:
            return False
        if "min" in cond and value < cond["min"]:
            return False
        return True
    if "matches" in cond:
        return isinstance(value, str) and re.fullmatch(cond["matches"], value) is not None
    raise PolicyError(f"condition on '{param}' has no operator")


def _validate_rule(rule: dict, seen_ids: set) -> None:
    if not isinstance(rule, dict):
        raise PolicyError("each rule must be a mapping")
    if "id" not in rule or not rule["id"]:
        raise PolicyError("every rule needs an 'id'")
    if rule["id"] in seen_ids:
        raise PolicyError(f"duplicate rule id '{rule['id']}'")
    if rule.get("action") not in ACTIONS:
        raise PolicyError(
            f"rule '{rule['id']}': action must be one of {ACTIONS}, "
            f"got {rule.get('action')!r}"
        )
    if "tool" not in rule and "server" not in rule:
        raise PolicyError(f"rule '{rule['id']}': needs a 'tool' or 'server' pattern")
    for cond in rule.get("where", []) or []:
        if not isinstance(cond, dict) or "param" not in cond:
            raise PolicyError(f"rule '{rule['id']}': each condition needs a 'param'")
        operators = [k for k in cond if k not in ("param",)]
        unknown = [k for k in operators if k not in CONDITION_KEYS]
        if unknown:
            raise PolicyError(
                f"rule '{rule['id']}': unknown condition key(s) {unknown}; "
                f"supported: {CONDITION_KEYS}"
            )
        if not operators:
            raise PolicyError(f"rule '{rule['id']}': condition on "
                              f"'{cond['param']}' has no operator")
        if "matches" in cond:
            try:
                re.compile(cond["matches"])
            except re.error as exc:
                raise PolicyError(
                    f"rule '{rule['id']}': bad regex {cond['matches']!r}: {exc}"
                ) from exc


class Policy:
    def __init__(self, default: str, rules: list[dict]):
        self.default = default
        self.rules = rules

    @classmethod
    def load(cls, path: Path) -> "Policy":
        try:
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise PolicyError(f"cannot parse {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise PolicyError("policy file must be a YAML mapping")

        default = data.get("default")
        if default not in DEFAULT_ACTIONS:
            raise PolicyError(
                f"'default' must be one of {DEFAULT_ACTIONS}, got {default!r}"
            )

        rules = data.get("rules") or []
        if not isinstance(rules, list):
            raise PolicyError("'rules' must be a list")
        seen_ids: set = set()
        for rule in rules:
            _validate_rule(rule, seen_ids)
            seen_ids.add(rule["id"])
        return cls(default=default, rules=rules)

    def evaluate(self, server: str, tool: str, arguments: dict) -> Decision:
        for rule in self.rules:
            if "tool" in rule and not fnmatchcase(tool, rule["tool"]):
                continue
            if "server" in rule and not fnmatchcase(server, rule["server"]):
                continue
            conditions = rule.get("where", []) or []
            if all(_condition_holds(c, arguments) for c in conditions):
                return Decision(action=rule["action"], rule_id=rule["id"])
        return Decision(action=self.default, rule_id="default")
