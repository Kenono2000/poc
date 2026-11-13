# Go Interview Cheat Sheet
## Polyglot Mental Translation
### Data Model
C#/TS/Python: `class` / `interface` / `BaseModel` Go: `type Req struct { ID string `json:"id"` }`
### Interface
Explicit: `type IFoo interface { … }` – implement by naming it. Implicit: any type with matching methods satisfies the interface.
### Cancellation
C#/TS/Python: `CancellationToken` / `AbortSignal` / `asyncio.wait_for` Go: `ctx context.Context` – always first function parameter.
## Async / Parallel
C#/TS/Python: `Task.WhenAll` / `Promise.all` / `asyncio.gather` Go: `go func(){}` + `sync.WaitGroup` or channel pipelines.
## Queues
C#/TS/Python: `Channel<T>` / `asyncio.Queue` Go: `ch := make(chan T, bufferSize)`
## Locking
C#/TS/Python: `lock (_mu)` / `asyncio.Lock` Go: `mu.Lock(); defer mu.Unlock()`
## Errors
C#/TS/Python: try/catch exceptions Go: return error, wrap with `%w`: `if err != nil { return fmt.Errorf("...: %w", err) }`
## Syntax Rules (7 must‑know)
1. Declaration Scope: `:=` only inside functions; `var` at package level.
2. Single Loop Construct: `for` covers all loops (classic, condition, infinite, range, channel).
3. Brace Placement: opening `{` on same line as `func`, `if`, or `for`.
4. Zero Unused Code: unused vars/imports cause compile error – use `_ = x` to discard.
5. Slice Backing Arrays: slicing shares underlying array; use `copy` for independent copy.
6. Append Assignment: always `s = append(s, v)` because `append` may reallocate.
7. Map Initialization: writes to nil map panic – initialize with `m := make(map[K]V)`
## Structs, Receivers & Error Handling
- Visibility: capitalized identifiers are exported.
- Receiver Choice: use pointer receivers (`func (s *Service) Method`) when struct holds `sync.Mutex`, channels, or mutable state.
- Comma‑Ok Idiom: `val, ok := m[key]` to safely check existence.
- Error Wrapping: define sentinel `var ErrNotFound = errors.New("not found")`; wrap with `%w` and check via `errors.Is`.
## Concurrency Core Primitives
### Fan‑Out / Fan‑In
```go
func RunAll(ctx context.Context, tasks []string) []string {
    results := make([]string, len(tasks))
    var wg sync.WaitGroup
    for i, t := range tasks {
        i, t := i, t // capture
        wg.Add(1)
        go func() {
            defer wg.Done()
            // do work, store in results[i]
        }()
    }
    wg.Wait()
    return results
}
```
### Non‑Blocking Channels & select
```go
select {
case queue <- job:
    return nil
case <-ctx.Done():
    return ctx.Err()
}
```
Channel Rule: only the producer closes (`close(ch)`); receivers drain via `for v := range ch`.
## Production Patterns
### Per‑Tenant Rate Limiter
Core: `sync.RWMutex` on `map[string]*bucket` + per‑bucket `sync.Mutex`. Double‑checked locking on bucket creation; background ticker janitor evicts idle tenants.
### Agent Tool Loop
`for turn := 0; turn < maxTurns; turn++` with `context.WithTimeout` per tool. Hard turn ceiling, per‑tool timeout, tool errors returned as messages, not panics.
### Bounded Worker Pool
Buffered `chan Task`, `N` worker goroutines, `sync.WaitGroup`. Back‑pressure via `select { case jobs <- job: default: return ErrQueueFull }`. Graceful drain: `close(jobs); wg.Wait()` with timeout handling.
### Stream Deduplicator
`map[string]time.Time` keyed by `DeviceID:CampaignID`. Check `now.Sub(lastSeen) < window` under lock; periodic sweep to prevent OOM.
### Strict HTTP JSON
```go
dec := json.NewDecoder(r.Body)
dec.DisallowUnknownFields()
```
Rejects unexpected fields – Go equivalent of Pydantic `extra="forbid"`.
## Live Coding Execution – ATOLA
A: Ask – clarify throughput, concurrency bounds, timeouts, retry expectations.
T: Think – discuss trade‑offs (global vs per‑tenant lock, back‑pressure).
O: Outline – sketch structs, interfaces, signatures first.
L: Leverage – use `context.Context` as first arg, `defer` cleanups, pre‑allocate slices.
A: Audit – review race conditions, goroutine leaks, nil checks, shutdown order.
## Top 5 Live‑Coding Traps
1. Goroutine leaks – always exit via `ctx.Done()` or closed channel.
2. Defer inside loops – runs at function return, not per iteration – wrap loop body.
3. Copying mutexes – never pass struct with `sync.Mutex` by value; use pointers.
4. Writing to closed channels – synchronize shutdown flag with mutex before close.
5. Unbounded maps – cache/rate‑limiter/dedup maps need TTL eviction to avoid OOM.
## Additional Sample Code
### 1. REST API Minimal Template (standard library)
```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
)

type Response struct {
    Message string `json:"message"`
}

func main() {
    http.HandleFunc("/api/hello", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(Response{Message: "Hello from REST API"})
    })
    log.Println("REST API listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```
Test: `curl http://localhost:8080/api/hello` → `{"message":"Hello from REST API"}`.
### 2. MCP Service Minimal Template (official Go SDK)
```bash
go mod init mcp-demo
go get github.com/modelcontextprotocol/go-sdk/mcp
```
```go
package main

import (
    "context"
    "log"
    "github.com/modelcontextprotocol/go-sdk/mcp"
)

type GreetInput struct {
    Name string `json:"name" jsonschema:"the name to greet"`
}

func Greet(ctx context.Context, req *mcp.CallToolRequest, input GreetInput) (*mcp.CallToolResult, any, error) {
    return &mcp.CallToolResult{
        Content: []mcp.Content{
            &mcp.TextContent{Text: "Hello, " + input.Name},
        },
    }, nil, nil
}

func main() {
    server := mcp.NewServer(&mcp.Implementation{Name: "demo-server", Version: "v0.0.1"}, nil)
    mcp.AddTool(server, &mcp.Tool{Name: "greet", Description: "Greet someone by name"}, Greet)
    if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
        log.Fatal(err)
    }
}
```
Runs via stdio; configure an MCP client to load `greet`.
### 3. Running Both in One Process (optional)
```go
func main() {
    go func() {
        http.HandleFunc("/api/hello", func(w http.ResponseWriter, r *http.Request) {
            w.Header().Set("Content-Type", "application/json")
            json.NewEncoder(w).Encode(Response{Message: "Hello from REST API"})
        })
        log.Fatal(http.ListenAndServe(":8080", nil))
    }()
    server := mcp.NewServer(&mcp.Implementation{Name: "demo-server", Version: "v0.0.1"}, nil)
    mcp.AddTool(server, &mcp.Tool{Name: "greet", Description: "Greet someone by name"}, Greet)
    http.Handle("/mcp", server.NewStreamableHTTPHandler())
    log.Fatal(http.ListenAndServe(":8090", nil))
}
```