"""
Pattern 3: Hybrid Search (Dense + Sparse), RRF & Grounding Guardrail
====================================================================
Core Interview Point:
- Dense vectors capture semantic meaning; Sparse (BM25/tsvector) captures exact error codes/IDs.
- Reciprocal Rank Fusion (RRF, k=60) merges both ranked lists without score calibration:
    RRF(d) = sum( 1 / (60 + rank_m(d)) )
- GroundingGuardrail regex-validates `[Doc: <ID>, Chunk <N>]` citations against retrieved chunks.
"""

from collections import defaultdict
import re

CITATION_RE = re.compile(r"\[Doc:\s*([A-Za-z0-9_-]+),\s*Chunk\s*(\d+)\]")


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse multiple ranked document ID lists using standard RRF (k=60)."""
    scores: dict[str, float] = defaultdict(float)
    for result_list in ranked_lists:
        for rank_idx, doc_id in enumerate(result_list, start=1):
            scores[doc_id] += 1.0 / (k + rank_idx)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def validate_grounding(llm_answer: str, authorized_doc_ids: set[str]) -> tuple[bool, str]:
    """Verify every claim citation exists in the caller's RBAC-authorized context."""
    if "I do not have sufficient information" in llm_answer:
        return True, "Valid explicit refusal on missing context"

    citations = CITATION_RE.findall(llm_answer)
    if not citations:
        return False, "Rejected: Missing mandatory [Doc: <ID>, Chunk <N>] citation"

    for doc_id, _ in citations:
        if doc_id not in authorized_doc_ids:
            return False, f"Rejected: Hallucinated or unauthorized citation '{doc_id}'"

    return True, f"Verified {len(citations)} grounded citation(s)"


if __name__ == "__main__":
    # Dense finds semantic concepts; Sparse finds exact error code 'ERR-502'
    dense_ranking = ["DOC-ARCH", "DOC-ERR-502", "DOC-ONBOARD"]
    sparse_ranking = ["DOC-ERR-502", "DOC-LOGS", "DOC-ARCH"]

    fused = reciprocal_rank_fusion([dense_ranking, sparse_ranking], k=60)
    print("RRF Hybrid Ranking:")
    for doc_id, score in fused:
        print(f"  {doc_id:<14} -> RRF Score: {score:.5f}")

    authorized = {"DOC-ARCH", "DOC-ERR-502"}
    good_resp = "Gateway timeouts trigger retry backoff [Doc: DOC-ERR-502, Chunk 1]."
    bad_resp = "Salary band is $250k [Doc: DOC-HR-SECRET, Chunk 2]."

    print("\nGrounding Check (Valid)  :", validate_grounding(good_resp, authorized))
    print("Grounding Check (Invalid):", validate_grounding(bad_resp, authorized))
