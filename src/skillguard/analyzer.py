"""Conflict evaluation and problem prediction engine."""

import re

from skillguard.models import ConflictReport, PredictionReport, ScanResult, SkillNode

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "use", "when",
    "with", "you", "your", "skill", "agent",
}

OPPOSING_PAIRS = [
    ({"minimal", "compact", "strip", "remove"}, {"verbose", "detailed", "add", "blank"}),
    ({"always"}, {"never"}),
]


def _keywords(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9_-]{3,}", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def evaluate_conflicts(skills: list[SkillNode]) -> list[ConflictReport]:
    """Evaluate name collisions, trigger overlaps, and rule contradictions."""
    conflicts: list[ConflictReport] = []

    # 1. Name collisions across scopes or duplicate definitions
    by_name: dict[str, list[SkillNode]] = {}
    for s in skills:
        by_name.setdefault(s.name.lower(), []).append(s)

    for name, group in by_name.items():
        if len(group) > 1:
            scopes = [g.scope for g in group]
            conflicts.append(
                ConflictReport(
                    severity="critical",
                    conflict_type="name_collision",
                    skills=[g.id for g in group],
                    message=f"Skill '{name}' is defined {len(group)} times across scopes: {', '.join(scopes)}.",
                    suggestion="Rename one skill or explicitly scope/disable the shadowed global skill.",
                )
            )

    # 2. Pairwise trigger overlap & rule contradiction
    kw_cache = {s.id: _keywords(s.description) for s in skills}
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            a, b = skills[i], skills[j]
            sim = _jaccard(kw_cache[a.id], kw_cache[b.id])
            if sim >= 0.45 and not (a.has_negative_guardrail and b.has_negative_guardrail):
                conflicts.append(
                    ConflictReport(
                        severity="warning",
                        conflict_type="trigger_overlap",
                        skills=[a.id, b.id],
                        message=f"Trigger descriptions overlap ({sim:.0%} keyword similarity).",
                        suggestion="Add 'Don't use for...' guardrails to disambiguate activation.",
                    )
                )

            # Check opposing imperatives on shared topic
            if sim >= 0.25 and a.imperatives and b.imperatives:
                a_imp = " ".join(a.imperatives).lower()
                b_imp = " ".join(b.imperatives).lower()
                for pos, neg in OPPOSING_PAIRS:
                    if (any(w in a_imp for w in pos) and any(w in b_imp for w in neg)) or (
                        any(w in b_imp for w in pos) and any(w in a_imp for w in neg)
                    ):
                        conflicts.append(
                            ConflictReport(
                                severity="warning",
                                conflict_type="rule_contradiction",
                                skills=[a.id, b.id],
                                message="Potentially opposing imperatives detected between overlapping skills.",
                                suggestion="Review ALWAYS/NEVER rules in both skills to ensure compatibility.",
                            )
                        )
                        break

    return conflicts


def predict_problems(skills: list[SkillNode], token_budget: int = 12000) -> list[PredictionReport]:
    """Predict context bloat, trigger ambiguity, missing guardrails, and brittle paths."""
    predictions: list[PredictionReport] = []
    total_tokens = sum(s.token_count for s in skills)

    if total_tokens > token_budget:
        predictions.append(
            PredictionReport(
                severity="critical",
                issue_type="token_bloat",
                target="registry",
                risk_score=min(100, int((total_tokens / token_budget) * 60)),
                message=f"Total skill footprint ({total_tokens} tokens) exceeds budget ({token_budget}).",
                suggestion="Archive unused skills or move large reference tables into references/.",
            )
        )

    for s in skills:
        if len(s.description) < 30:
            predictions.append(
                PredictionReport(
                    severity="warning",
                    issue_type="trigger_ambiguity",
                    target=s.id,
                    risk_score=65,
                    message="Description is too short (<30 chars); agent may under-trigger this skill.",
                    suggestion="Expand description with explicit trigger phrases and use cases.",
                )
            )
        if not s.has_negative_guardrail and len(s.description) > 0:
            predictions.append(
                PredictionReport(
                    severity="info",
                    issue_type="missing_guardrail",
                    target=s.id,
                    risk_score=30,
                    message="No negative guardrail ('Don't use for...') found in description.",
                    suggestion="Add a negative boundary to prevent false-positive activation.",
                )
            )
        if s.hardcoded_paths:
            predictions.append(
                PredictionReport(
                    severity="warning",
                    issue_type="brittle_path",
                    target=s.id,
                    risk_score=55,
                    message=(
                        f"Found {len(s.hardcoded_paths)} hardcoded absolute path(s) "
                        f"(e.g., {s.hardcoded_paths[0]})."
                    ),
                    suggestion="Replace user/machine-specific paths with relative paths or env vars.",
                )
            )

    return predictions


def analyze(skills: list[SkillNode], token_budget: int = 12000) -> ScanResult:
    """Run full conflict evaluation and problem prediction."""
    return ScanResult(
        skills=skills,
        conflicts=evaluate_conflicts(skills),
        predictions=predict_problems(skills, token_budget=token_budget),
        total_tokens=sum(s.token_count for s in skills),
    )
