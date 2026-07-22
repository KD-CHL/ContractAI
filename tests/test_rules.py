from __future__ import annotations

import pytest

from contract_guard.domain import Clause, RiskLevel
from contract_guard.services.rules import (
    DEFAULT_RULE_PATTERNS,
    RulePattern,
    RuleScanner,
)


def _clause(text: str, *, start: int = 0) -> Clause:
    return Clause(
        clause_id="clause-test",
        ordinal=1,
        text=text,
        start_offset=start,
        end_offset=start + len(text),
    )


def test_rule_pattern_is_independently_matchable_with_offsets() -> None:
    rule = RulePattern(
        rule_id="custom",
        pattern=r"自动\s*续期",
        title="自动续期",
        description="测试规则",
        category="term",
        risk_level=RiskLevel.MEDIUM,
        recommendation="人工复核",
    )

    text = "合同期限届满后将自动续期一年。"
    match = next(rule.iter_matches(text))

    assert rule.matches(text)
    assert match.text == "自动续期"
    assert text[match.start : match.end] == match.text
    assert not rule.matches("合同期限届满后终止。")


@pytest.mark.parametrize(
    ("rule_id", "text"),
    [
        ("unlimited-liability", "乙方承担无限责任。"),
        ("unilateral-termination", "甲方有权随时单方解除本合同。"),
        ("automatic-renewal", "期限届满后自动续期。"),
        ("deemed-acceptance", "逾期未提出异议即视为验收合格。"),
        ("unilateral-amendment", "平台有权随时单方修改服务条款。"),
        ("exclusive-interpretation", "最终解释权归甲方所有。"),
    ],
)
def test_default_patterns_detect_their_target(rule_id: str, text: str) -> None:
    pattern = next(item for item in DEFAULT_RULE_PATTERNS if item.rule_id == rule_id)
    assert pattern.matches(text)


def test_rule_scanner_emits_exact_unverified_contract_evidence() -> None:
    prefix = "前置文本\n"
    text = "甲方有权随时单方解除本合同。"
    clause = _clause(text, start=len(prefix))

    findings = RuleScanner().scan_clause(clause)
    finding = next(item for item in findings if item.rule_id == "unilateral-termination")
    evidence = finding.evidence[0]

    assert evidence.quote in text
    assert evidence.start_offset == len(prefix) + text.index(evidence.quote)
    assert evidence.end_offset == evidence.start_offset + len(evidence.quote)
    assert evidence.verified is False
    assert finding.clause_ids == [clause.clause_id]


def test_rule_scanner_rejects_duplicate_rule_ids() -> None:
    rule = DEFAULT_RULE_PATTERNS[0]
    with pytest.raises(ValueError, match="rule ids must be unique"):
        RuleScanner([rule, rule])
