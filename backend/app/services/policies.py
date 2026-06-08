from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Agent, Policy


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    matched_rule: dict[str, Any] | None = None


class PolicyEngine:
    valid_effects = {"allow": "allowed", "deny": "denied", "approval_required": "approval_required"}

    def evaluate_document(
        self, document: str, *, agent: str, tool: str, action: str, resource: str
    ) -> PolicyResult:
        try:
            policy = yaml.safe_load(document) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid policy YAML: {exc}") from exc
        if not isinstance(policy, dict):
            raise ValueError("Policy must be a YAML mapping")
        rules = policy.get("rules", [])
        if not isinstance(rules, list):
            raise ValueError("Policy rules must be a list")
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("Each policy rule must be a mapping")
            effect = rule.get("effect")
            if effect not in self.valid_effects:
                raise ValueError(f"Unsupported policy effect: {effect}")
            if not self._matches(rule.get("agent", "*"), agent):
                continue
            if not self._matches(rule.get("tool", "*"), tool):
                continue
            if not self._matches_any(rule.get("actions", ["*"]), action):
                continue
            if not self._matches_any(rule.get("resources", ["*"]), resource):
                continue
            return PolicyResult(self.valid_effects[effect], rule)
        default = policy.get("default", "deny")
        if default not in self.valid_effects:
            raise ValueError(f"Unsupported default policy effect: {default}")
        return PolicyResult(self.valid_effects[default])

    def evaluate(
        self,
        db: Session,
        *,
        tenant_id,
        agent: Agent,
        tool: str,
        action: str,
        resource: str,
    ) -> PolicyResult:
        policies = list(
            db.scalars(
                select(Policy)
                .where(Policy.tenant_id == tenant_id, Policy.status == "active")
                .order_by(Policy.created_at.desc())
            )
        )
        if not policies:
            return PolicyResult("denied")
        return self.evaluate_document(
            policies[0].policy_yaml,
            agent=agent.name,
            tool=tool,
            action=action,
            resource=resource,
        )

    @staticmethod
    def _matches(pattern: str, value: str) -> bool:
        return fnmatchcase(value, pattern)

    def _matches_any(self, patterns: list[str] | str, value: str) -> bool:
        if isinstance(patterns, str):
            patterns = [patterns]
        return any(self._matches(pattern, value) for pattern in patterns)


policy_engine = PolicyEngine()
