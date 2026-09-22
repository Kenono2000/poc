import numpy as np
from typing import List

def truncate_and_normalize_matryoshka(
    embedding: List[float], 
    target_dim: int = 1536
) -> List[float]:
    """
    Slices a 3072-dimensional Matryoshka vector to target_dim
    and re-normalizes to unit length for SIMD dot-product acceleration.
    """
    # 1. Truncate prefix dimensions
    truncated = np.array(embedding[:target_dim], dtype=np.float32)
    
    # 2. Compute L2 norm
    norm = np.linalg.norm(truncated)
    if norm == 0:
        return truncated.tolist()
    
    # 3. Unit-normalize: length == 1.0
    normalized = truncated / norm
    return normalized.tolist()