"""Deterministic, independently testable contract-risk rules."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field

from contract_guard.domain import (
    Clause,
    Evidence,
    FindingSource,
    RiskFinding,
    RiskLevel,
)


@dataclass(frozen=True, slots=True)
class RuleMatch:
    """A source-relative regular-expression match."""

    rule_id: str
    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class RulePattern:
    """One declarative rule with its user-facing review metadata."""

    rule_id: str
    pattern: str
    title: str
    description: str
    category: str
    risk_level: RiskLevel
    recommendation: str
    knowledge_refs: tuple[str, ...] = ()
    flags: int = re.IGNORECASE | re.MULTILINE
    _compiled: re.Pattern[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id cannot be blank")
        try:
            compiled = re.compile(self.pattern, self.flags)
        except re.error as exc:
            raise ValueError(f"invalid pattern for rule {self.rule_id}: {exc}") from exc
        object.__setattr__(self, "_compiled", compiled)

    def iter_matches(self, text: str) -> Iterator[RuleMatch]:
        """Yield non-empty, trimmed matches with offsets into ``text``."""

        for match in self._compiled.finditer(text):
            raw = match.group(0)
            left_trim = len(raw) - len(raw.lstrip())
            right_trimmed = raw.rstrip()
            start = match.start() + left_trim
            end = match.start() + len(right_trimmed)
            if end <= start:
                continue
            yield RuleMatch(
                rule_id=self.rule_id,
                text=text[start:end],
                start=start,
                end=end,
            )

    def matches(self, text: str) -> bool:
        """Return whether the rule matches, without constructing findings."""

        return next(self.iter_matches(text), None) is not None


DEFAULT_RULE_PATTERNS: tuple[RulePattern, ...] = (
    RulePattern(
        rule_id="unlimited-liability",
        pattern=(
            r"(?:承担|负有|应负)?\s*无限(?:连带)?(?:赔偿)?责任"
            r"|(?:unlimited|without\s+limit(?:ation)?)\s+liabilit(?:y|ies)"
        ),
        title="责任范围可能未设上限",
        description="条款使用了无限责任表述，责任边界可能明显扩大。",
        category="liability",
        risk_level=RiskLevel.HIGH,
        recommendation="核对责任上限、除外情形及其与合同金额的比例。",
    ),
    RulePattern(
        rule_id="unilateral-termination",
        pattern=(
            r"(?:甲方|乙方|任何一方|一方).{0,24}?"
            r"(?:有权)?.{0,12}?(?:随时|单方|无理由).{0,12}?"
            r"(?:解除|终止)(?:本合同|合同)?"
            r"|(?:either\s+party|party\s+[ab]).{0,30}?"
            r"(?:unilaterally|at\s+any\s+time).{0,20}?terminate"
        ),
        title="可能存在单方任意解约权",
        description="条款赋予一方随时或单方终止合同的权利。",
        category="termination",
        risk_level=RiskLevel.HIGH,
        recommendation="核对双方权利是否对等，并明确通知期与补救机制。",
    ),
    RulePattern(
        rule_id="automatic-renewal",
        pattern=(
            r"(?:自动|默示)\s*(?:续期|续约|延长)"
            r"|automat(?:ic|ically)\s+renew(?:al|s|ed)?"
        ),
        title="合同可能自动续期",
        description="条款包含自动续期安排，可能产生未主动确认的后续期限。",
        category="term",
        risk_level=RiskLevel.MEDIUM,
        recommendation="核对续期周期、提醒机制和拒绝续期的通知期限。",
    ),
    RulePattern(
        rule_id="deemed-acceptance",
        pattern=(
            r"(?:逾期|期限内)未.{0,18}?(?:提出|回复|通知|异议)"
            r".{0,10}?(?:视为|即视为).{0,12}?(?:验收合格|认可|同意|接受)"
            r"|deemed\s+(?:accepted|approved)"
        ),
        title="沉默可能被视为验收或同意",
        description="条款将未及时回复直接视为验收、认可或同意。",
        category="acceptance",
        risk_level=RiskLevel.MEDIUM,
        recommendation="核对验收标准、异议期限及逾期后仍可主张的缺陷责任。",
    ),
    RulePattern(
        rule_id="unilateral-amendment",
        pattern=(
            r"(?:甲方|乙方|平台|一方).{0,24}?(?:有权)?"
            r".{0,10}?(?:随时|单方).{0,10}?(?:修改|变更|调整)"
            r"|(?:may|can).{0,20}?unilaterally.{0,20}?(?:amend|modify)"
        ),
        title="可能存在单方变更权",
        description="条款允许一方单独修改合同内容或关键安排。",
        category="amendment",
        risk_level=RiskLevel.HIGH,
        recommendation="要求明确变更范围、提前通知、异议及退出机制。",
    ),
    RulePattern(
        rule_id="exclusive-interpretation",
        pattern=(
            r"最终解释权.{0,12}?(?:归|属于).{0,16}?(?:所有|享有)"
            r"|sole\s+(?:right|authority)\s+to\s+interpret"
        ),
        title="一方保留最终解释权",
        description="条款将合同解释权集中授予一方。",
        category="interpretation",
        risk_level=RiskLevel.HIGH,
        recommendation="删除单方最终解释安排，改为双方协商或约定争议解决机制。",
    ),
)


class RuleScanner:
    """Run deterministic patterns and emit evidence-backed findings."""

    def __init__(
        self,
        patterns: Sequence[RulePattern] = DEFAULT_RULE_PATTERNS,
    ) -> None:
        self.patterns = tuple(patterns)
        rule_ids = [rule.rule_id for rule in self.patterns]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("rule ids must be unique")

    def scan_clause(self, clause: Clause) -> list[RiskFinding]:
        findings: list[RiskFinding] = []
        for rule in self.patterns:
            for match in rule.iter_matches(clause.text):
                absolute_start = clause.start_offset + match.start
                absolute_end = clause.start_offset + match.end
                finding_id = _stable_identifier(
                    "rule",
                    rule.rule_id,
                    clause.clause_id,
                    str(absolute_start),
                    str(absolute_end),
                )
                findings.append(
                    RiskFinding(
                        finding_id=finding_id,
                        title=rule.title,
                        description=rule.description,
                        category=rule.category,
                        risk_level=rule.risk_level,
                        source=FindingSource.RULE,
                        rule_id=rule.rule_id,
                        context_refs=list(rule.knowledge_refs),
                        clause_ids=[clause.clause_id],
                        evidence=[
                            Evidence(
                                clause_id=clause.clause_id,
                                quote=match.text,
                                start_offset=absolute_start,
                                end_offset=absolute_end,
                            )
                        ],
                        recommendation=rule.recommendation,
                        confidence=1.0,
                    )
                )
        return findings

    def scan(self, clauses: Iterable[Clause]) -> list[RiskFinding]:
        return [finding for clause in clauses for finding in self.scan_clause(clause)]


def _stable_identifier(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


__all__ = [
    "DEFAULT_RULE_PATTERNS",
    "RuleMatch",
    "RulePattern",
    "RuleScanner",
]
