"""Data models for SkillGuard."""

from dataclasses import asdict, dataclass, field
from typing import Literal

Scope = Literal["global", "project", "plugin", "builtin"]
Severity = Literal["critical", "warning", "info"]


@dataclass
class SkillNode:
    """Represents a parsed SKILL.md file."""

    id: str
    name: str
    scope: Scope
    path: str
    description: str
    body: str
    token_count: int
    imperatives: list[str] = field(default_factory=list)
    has_negative_guardrail: bool = False
    hardcoded_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConflictReport:
    """Represents a detected conflict between two or more skills."""

    severity: Severity
    conflict_type: Literal["name_collision", "trigger_overlap", "rule_contradiction"]
    skills: list[str]
    message: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PredictionReport:
    """Represents a predicted problem for a skill or the overall registry."""

    severity: Severity
    issue_type: Literal[
        "token_bloat",
        "trigger_ambiguity",
        "missing_guardrail",
        "brittle_path",
    ]
    target: str
    risk_score: int
    message: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    """Aggregated result of scanning, conflict evaluation, and prediction."""

    skills: list[SkillNode]
    conflicts: list[ConflictReport]
    predictions: list[PredictionReport]
    total_tokens: int

    def to_dict(self) -> dict:
        return {
            "skills": [s.to_dict() for s in self.skills],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "predictions": [p.to_dict() for p in self.predictions],
            "total_tokens": self.total_tokens,
        }
