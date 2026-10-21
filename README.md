# 🛡️ Enterprise Zero-Trust AI & Systems Architecture — 1-Page Coding Cheat Sheet
Consolidated from [`c:\src\poc\practice\py\`](file:///c:/src/poc/practice/py/) (`01`–`07`). Every snippet uses **100% Python Standard Library** and represents the exact production invariant from [`enterprise-rag-pgvector-rbac`](file:///c:/src/enterprise-rag-pgvector-rbac/README.md).
**Quick Navigation:** [1. Vector RBAC](#1-shift-left-in-database-vector-rbac-01_zero_trust_vector_rbacpy) • [2. PKCE & State](#2-stateless-oauth-20-pkce--hmac-signed-state-02_stateless_pkce_sessionpy) • [3. Hybrid RRF](#3-hybrid-search-rrf-k60--citation-guardrail-03_hybrid_rrf_and_groundingpy) • [4. SHA-256 Ingest](#4-o1-memory-sha-256-ingestion--exponential-backoff-04_idempotent_sha256_ingestionpy) • [5. Async Pool](#5-event-loop-scoped-async-clientpool-manager-05_loop_scoped_async_poolpy) • [6. AST Agent](#6-self-healing-sdlc-agent--pre-execution-ast-gate-06_sdlc_agent_ast_guardrailspy) • [7. Multi-Cloud](#7-quad-mode-multi-cloud-zero-trust-rbac-router-07_multicloud_rbac_routerpy) • [Matrix](#-quick-reference-summary-matrix)

### 1. Shift-Left In-Database Vector RBAC ([`01_zero_trust_vector_rbac.py`](file:///c:/src/poc/practice/py/01_zero_trust_vector_rbac.py))
* **Why**: Post-filtering after Top-$K$ vector search causes **Recall Starvation** (drops restricted Top-$K$ hits, returning `0` results) and loads unauthorized data into RAM.
* **Pattern**: Allowlist-sanitize roles $\rightarrow$ short-circuit empty roles $\rightarrow$ **pre-filter via GIN index** (`?|`) *before* HNSW cosine distance (`<=>`).
```python
KNOWN_ROLES = {"admin", "finance", "engineering", "public"}
def shift_left_rbac_search(query_vec: list[float], chunks: list, raw_roles: list[str], top_k: int = 5):
    roles = {r.strip().lower() for r in raw_roles if r.strip().lower() in KNOWN_ROLES}
    if not roles: return []  # Zero-Trust invariant: never touch DB/storage if roles are empty
    authorized = (c for c in chunks if c.allowed_roles & roles)  # 1. Pre-filter (SQL: WHERE d.allowed_roles ?| $2::text[])
    return sorted(authorized, key=lambda c: cosine_similarity(query_vec, c.embedding), reverse=True)[:top_k]  # 2. HNSW scan
```
```text
❌ Post-Filter (Recall Starvation): []  <-- Dropped top-1 admin doc, returned 0!
✅ Shift-Left In-DB RBAC          : ['ENG-RUNBOOK-01'] <-- Pre-filtered, returned authorized top-1!
🛡️ Empty Roles Short-Circuit      : []
```

### 2. Stateless OAuth 2.0 PKCE & HMAC-Signed State ([`02_stateless_pkce_session.py`](file:///c:/src/poc/practice/py/02_stateless_pkce_session.py))
* **Why**: Eliminates server-side Redis/session memory across OAuth redirects, F5 reloads, and multi-pod horizontal scaling while preventing CSRF and auth-code interception (RFC 7636).
* **Pattern**: `S256` challenge derivation + self-contained `{b64url_payload}.{b64url_hmac}` verified via `hmac.compare_digest` (constant-time).
```python
def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    return verifier, b64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
def encode_stateless_state(verifier: str, secret: bytes) -> str:
    b64_payload = b64url_encode(json.dumps({"v": verifier, "iat": int(time.time())}).encode())
    sig = b64url_encode(hmac.new(secret, b64_payload.encode(), hashlib.sha256).digest())
    return f"{b64_payload}.{sig}"
def decode_stateless_state(token: str, secret: bytes, ttl: int = 300) -> str:
    b64_payload, b64_sig = token.split(".", 1)
    expected = b64url_encode(hmac.new(secret, b64_payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(b64_sig, expected): raise ValueError("Invalid signature")
    data = json.loads(b64url_decode(b64_payload))
    if time.time() - data["iat"] > ttl: raise ValueError("Expired state")
    return data["v"]
```
```text
PKCE Challenge (S256) : H8h2aXsTCSaan1_ZickAi_gtNZTZFESMp2F9Pgk5sLw
Stateless Signed State: eyJ2IjoiN1BOWjdYRVotd09JdjZWRFY4MFVrdF91cnMxM...
Verifier Roundtrip OK : True
```

### 3. Hybrid Search (RRF $k=60$) & Citation Guardrail ([`03_hybrid_rrf_and_grounding.py`](file:///c:/src/poc/practice/py/03_hybrid_rrf_and_grounding.py))
* **Why**: Dense vectors capture semantic meaning; Sparse (`tsvector`/BM25) captures exact SKUs/error codes (`ERR-502`). RRF merges rankings without score normalization: $\text{RRF}(d) = \sum \frac{1}{60 + \text{rank}_m(d)}$.
* **Pattern**: `defaultdict(float)` rank accumulation + regex verification of `[Doc: <ID>, Chunk <N>]` against RBAC-authorized IDs.
```python
CITATION_RE = re.compile(r"\[Doc:\s*([A-Za-z0-9_-]+),\s*Chunk\s*(\d+)\]")
def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for result_list in ranked_lists:
        for rank, doc_id in enumerate(result_list, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
def validate_grounding(answer: str, authorized_ids: set[str]) -> bool:
    if "I do not have sufficient information" in answer: return True
    citations = CITATION_RE.findall(answer)
    return bool(citations) and all(doc_id in authorized_ids for doc_id, _ in citations)
```
```text
RRF Hybrid Ranking:
  DOC-ERR-502    -> RRF Score: 0.03252
  DOC-ARCH       -> RRF Score: 0.03227
  DOC-LOGS       -> RRF Score: 0.01613
  DOC-ONBOARD    -> RRF Score: 0.01587
Grounding Check (Valid)  : (True, 'Verified 1 grounded citation(s)')
Grounding Check (Invalid): (False, "Rejected: Hallucinated or unauthorized citation 'DOC-HR-SECRET'")
```

### 4. $O(1)$ Memory SHA-256 Ingestion & Exponential Backoff ([`04_idempotent_sha256_ingestion.py`](file:///c:/src/poc/practice/py/04_idempotent_sha256_ingestion.py))
* **Why**: Streaming 64KB blocks prevents OOM on large PDFs; B-Tree hash lookup skips unchanged files in $O(1)$ and purges stale chunks on edits; backoff survives HTTP `429`/`503`.
* **Pattern**: Walrus operator `while chunk := stream.read(65536)` + generator batch slicing + $2^{\text{attempt}-1}$ exponential delay.
```python
def compute_stream_sha256(stream: io.BytesIO, block_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    while chunk := stream.read(block_size): hasher.update(chunk)
    return hasher.hexdigest()
def call_with_backoff(fn, max_attempts: int = 3, base_delay: float = 1.0):
    for attempt in range(1, max_attempts + 1):
        try: return fn()
        except RuntimeError:
            if attempt == max_attempts: raise
            time.sleep(base_delay * (2 ** (attempt - 1)))
```
```text
1st Run : INDEXED (New document) [hash=60329bc854...]
2nd Run : SKIPPED (Unchanged SHA-256)
3rd Run : RE-INDEXED (Purged stale chunks) [hash=924a78c1fe...]
  [Retry 1/3] Recovered from transient error: HTTP 429 Too Many Requests
  [Retry 2/3] Recovered from transient error: HTTP 429 Too Many Requests
Backoff : [[0.1, 0.2]]
```

### 5. Event-Loop-Scoped Async Client/Pool Manager ([`05_loop_scoped_async_pool.py`](file:///c:/src/poc/practice/py/05_loop_scoped_async_pool.py))
* **Why**: Multi-threaded runners (Streamlit, worker pools) recycle asyncio loops across turns; global `AsyncOpenAI` or `asyncpg.Pool` singletons crash with `RuntimeError: Event loop is closed`.
* **Pattern**: Key clients by `asyncio.get_running_loop()` and garbage-collect closed loops (`lp.is_closed()`).
```python
class LoopScopedManager:
    def __init__(self, factory):
        self._factory, self._clients = factory, {}
    def get_client(self):
        loop = asyncio.get_running_loop()
        for stale in [lp for lp in self._clients if lp.is_closed()]: del self._clients[stale]
        if loop not in self._clients: self._clients[loop] = self._factory()
        return self._clients[loop]
```
```text
Turn 1: Bound safely to active loop 1409568435984 (active cached loops=1)
Turn 2: Bound safely to active loop 1409602898192 (active cached loops=1)
Loop recycled cleanly across turns: True (Cached loops remaining: 1)
```

### 6. Self-Healing SDLC Agent & Pre-Execution AST Gate ([`06_sdlc_agent_ast_guardrails.py`](file:///c:/src/poc/practice/py/06_sdlc_agent_ast_guardrails.py))
* **Why**: Autonomous coding agents must never execute untrusted LLM code before static verification.
* **Pattern**: Path containment (`Path.is_relative_to`) + regex secret scan + `ast.walk()` sink blocking (`eval`/`exec`/`__import__`) $\rightarrow$ `pytest` execution $\rightarrow$ bounded 3x traceback repair loop.
```python
BANNED_CALLS = {"eval", "exec", "__import__", "compile"}
def is_safe_path(file_path: str, root: Path) -> bool:
    target = (root / file_path).resolve()
    return target.is_relative_to(root.resolve()) and ".git" not in target.parts
def audit_patch(code: str) -> list[str]:
    return [f"Banned sink: {n.func.id}()" for n in ast.walk(ast.parse(code))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in BANNED_CALLS]
```
```text
[Attempt 1] Auditing proposed patch...
  ❌ Security Gate Blocked: ['Banned execution sink: eval()']
[Attempt 2] Auditing proposed patch...
  🔧 Test failed (Expected add(2, 3) == 5) -> Routing traceback to repair_patches...
[Attempt 3] Auditing proposed patch...
  ✅ Audit & Pytest passed! Opening Pull Request.
Final Workflow Status: PR_OPENED
```

### 7. Quad-Mode Multi-Cloud Zero-Trust RBAC Router ([`07_multicloud_rbac_router.py`](file:///c:/src/poc/practice/py/07_multicloud_rbac_router.py))
* **Why**: Enables zero-downtime `.env` cutover (`RETRIEVAL_BACKEND`) across 4 enterprise vector clouds while preserving strict pre-filtered RBAC.
```python
def build_rbac_filter(backend: str, user_roles: list[str]):
    roles = sorted({r.strip().lower() for r in user_roles if r.strip()})
    if not roles: return None  # Universal Zero-Trust short-circuit
    match backend:
        case "pgvector":   return {"sql": "d.allowed_roles ?| $2::text[]", "param": roles}
        case "azure":      return f"allowed_roles/any(r: {' or '.join(f'r eq {r!r}' for r in roles)})"
        case "gcp":        return [{"namespace": "allowed_roles", "allowList": roles}]  # Vertex ScaNN
        case "databricks": return json.dumps({"OR": [{"allowed_roles": r} for r in roles]})
```
```text
[PGVECTOR  ] -> {'sql_where': 'd.allowed_roles ?| $2::text[]', 'bind_param_2': ['engineering', 'finance']}
[AZURE     ] -> allowed_roles/any(r: r eq 'engineering' or r eq 'finance')
[GCP       ] -> [{'namespace': 'allowed_roles', 'allowList': ['engineering', 'finance']}]
[DATABRICKS] -> {"OR": [{"allowed_roles": "engineering"}, {"allowed_roles": "finance"}]}
[EMPTY ROLES] -> None (Short-circuited!)
```

### ⚡ Quick Reference Summary Matrix
| # | Core Problem | Engineering Solution | Key Python Stdlib / SQL Primitive |
| :-: | :--- | :--- | :--- |
| **01** | Post-filter Recall Starvation & RAM leaks | Shift-Left GIN Pre-Filter + HNSW | `WHERE d.allowed_roles ?\| $2::text[]` |
| **02** | Stateful OAuth sessions break on F5/scale-out | Stateless HMAC-Signed PKCE State | `hmac.compare_digest`, `hashlib.sha256` |
| **03** | Dense misses SKUs; LLMs hallucinate citations | RRF ($k=60$) + Regex Citation Guard | `1.0 / (60 + rank)`, `re.findall` |
| **04** | Large file OOM, duplicate indexing & HTTP 429 | 64KB Stream Hash + Exp Backoff | `while chunk := f.read(65536)` |
| **05** | `RuntimeError: Event loop is closed` | Loop-Keyed Client Dictionary | `asyncio.get_running_loop()`, `is_closed()` |
| **06** | Untrusted LLM patch RCE & path traversal | Pre-Exec AST Walk + Sandbox Check | `ast.walk(ast.parse(code))`, `is_relative_to` |
| **07** | Vendor lock-in across cloud vector DBs | Structural Pattern Matching Router | `match backend:` (`pgvector`/`azure`/`gcp`/`dbx`) |
