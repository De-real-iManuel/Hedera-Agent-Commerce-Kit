"""
hack/compliance/engine.py
--------------------------
ComplianceEngine — runs a configurable list of compliance rule callables
against a Quote + Mirror Node transaction dict and returns a
ComplianceCheckResult.

Rules are plain callables with the signature:
  (quote: Quote, tx_data: dict) -> ComplianceRule

This allows rules to be added, removed, or overridden at container
construction time without modifying the engine itself.
"""

from __future__ import annotations

import time
from typing import Callable

from ..models.compliance import ComplianceCheckResult, ComplianceRule
from ..models.quote import Quote


# Type alias for a compliance rule callable
ComplianceRuleChecker = Callable[[Quote, dict], ComplianceRule]


class ComplianceEngine:
    """
    Runs compliance rules and aggregates the results.

    Args:
        rules: List of rule callables.  Each must accept (Quote, dict) and
               return a ComplianceRule.  Defaults to an empty list (no rules).
    """

    def __init__(self, rules: list[ComplianceRuleChecker] | None = None) -> None:
        self._rules: list[ComplianceRuleChecker] = rules or []

    async def check(
        self,
        quote: Quote,
        transaction_id: str,
        tx_data: dict,
    ) -> ComplianceCheckResult:
        """
        Execute all configured rules against *quote* and *tx_data*.

        The ``passed`` field on the result is True only when every rule passes.
        Rules are executed in order; all rules run even if an earlier one fails
        so that callers receive a complete picture.

        Args:
            quote:          The Quote to evaluate.
            transaction_id: The transaction ID being checked (recorded in result).
            tx_data:        Raw Mirror Node transaction dict.

        Returns:
            A ComplianceCheckResult with per-rule outcomes.
        """
        rule_results: list[ComplianceRule] = []
        for rule_fn in self._rules:
            try:
                result = rule_fn(quote, tx_data)
            except Exception as exc:  # noqa: BLE001
                # A broken rule should not crash the engine — record it as failed
                result = ComplianceRule(
                    rule_id=getattr(rule_fn, "__name__", "unknown"),
                    name=getattr(rule_fn, "__name__", "unknown"),
                    passed=False,
                    detail=f"Rule raised an exception: {exc}",
                )
            rule_results.append(result)

        all_passed = all(r.passed for r in rule_results)
        return ComplianceCheckResult(
            quote_id=quote.quote_id,
            transaction_id=transaction_id,
            passed=all_passed,
            rules=rule_results,
            checked_at=int(time.time()),
        )
