# Go Interview Cheat Sheet
## Polyglot Mental Translation
| Concept | C# / TS / Python | Go |
| :--- | :--- | :--- |
| **Data Model** | `class` / `interface` / `BaseModel` | `type Req struct { ID string ` + "`json:\"id\"`" + ` }` |
| **Interface** | Explicit: `type IFoo interface { … }` | Implicit: matching methods satisfy interface |
| **Cancellation** | `CancellationToken` / `AbortSignal` / `asyncio.wait_for` | `ctx context.Context` (always 1st param) |
| **Async/Parallel** | `Task.WhenAll` / `Promise.all` / `asyncio.gather` | `go func(){}` + `sync.WaitGroup` / channels |
| **Queues** | `Channel<T>` / `asyncio.Queue` | `ch := make(chan T, bufferSize)` |
| **Locking** | `lock (_mu)` / `asyncio.Lock` | `mu.Lock(); defer mu.Unlock()` |
| **Errors** | try/catch exceptions | Multiple return: `if err != nil { return fmt.Errorf("...: %w", err) }` |
## Syntax Rules (7 must‑know)
1. **Scope**: `:=` inside functions only; `var` at package level.
2. **Loop**: `for` is the only loop construct (condition, infinite, range, channel).
3. **Braces**: `{` must be on same line as `func`, `if`, or `for`.
4. **Zero Unused**: Unused vars/imports fail build; discard via `_ = x`.
5. **Slices**: Slicing shares underlying array; use `copy()` for clone.
6. **Append**: Always `s = append(s, v)` as reallocations occur.
7. **Maps**: Nil map writes panic; initialize via `make(map[K]V)`.
## Structs, Receivers & Error Handling
- **Visibility**: Capitalized identifiers are exported.
- **Receivers**: Use pointer receiver `func (s *Service)` for mutexes, channels, mutable state.
- **Comma‑Ok**: `val, ok := m[key]` safely checks map/channel existence.
- **Errors**: Declare sentinel `var ErrNotFound = errors.New(...)`; wrap `%w`, check `errors.Is`.
## Concurrency Core Primitives
### Fan‑Out / Fan‑In with Non‑Blocking Select
```go
func RunAll(ctx context.Context, tasks []string) []string {
	results := make([]string, len(tasks))
	var wg sync.WaitGroup
	queue := make(chan struct {
		idx int
		val string
	}, len(tasks))

	for i, t := range tasks {
		i, t := i, t
		wg.Add(1)
		go func() {
			defer wg.Done()
			result := process(t)
			select {
			case queue <- struct {
				idx int
				val string
			}{idx: i, val: result}:
			case <-ctx.Done():
				return
			}
		}()
	}

	go func() {
		wg.Wait()
		close(queue)
	}()

	for {
		select {
		case item, ok := <-queue:
			if !ok {
				return results
			}
			results[item.idx] = item.val
		case <-ctx.Done():
			return results
		}
	}
}

func process(t string) string {
	return t
}
```
## Production Patterns
- **Rate Limiter**: `sync.RWMutex` on `map[string]*bucket` + per-bucket `sync.Mutex`. Double-check lock on create; ticker sweeps idle tenants.
- **Agent Loop**: `for turn := 0; turn < maxTurns; turn++` with `context.WithTimeout` per tool; return tool errors as messages, not panics.
- **Worker Pool**: Buffered `chan Task`, `N` workers, `sync.WaitGroup`. Backpressure via `select { case jobs <- job: default: return ErrQueueFull }`.
- **Deduplicator**: `map[string]time.Time` keyed by ID. Check `now.Sub(lastSeen) < window` under lock; periodic sweep.
- **Strict JSON**: `dec := json.NewDecoder(r.Body); dec.DisallowUnknownFields()`.
## Live Coding Execution – ATOLA
- **A (Ask)**: Clarify throughput, concurrency bounds, timeouts, retry policy.
- **T (Think)**: Evaluate trade-offs (global vs per-tenant locks, backpressure).
- **O (Outline)**: Sketch structs, interfaces, method signatures first.
- **L (Leverage)**: `context.Context` 1st arg, `defer` cleanups, pre-allocate slices.
- **A (Audit)**: Review race conditions (`-race`), goroutine leaks, nil checks, shutdown order.
## Top 5 Live‑Coding Traps
1. **Goroutine leaks**: Always exit via `ctx.Done()` or channel close.
2. **Defer in loops**: Executes at function return, not per loop iteration; wrap loop body.
3. **Copying mutex**: Never pass structs with `sync.Mutex` by value; use pointers.
4. **Closed channels**: Writing to a closed channel panics; synchronize shutdown before close.
5. **Unbounded maps**: Cache, rate-limit, and dedup maps require TTL eviction to avoid OOM.
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
Test: `curl http://localhost:8080/api/hello` → `{"message":"Hello from REST API"}`
### 2. MCP Service Minimal Template (official Go SDK)
```bash
go mod init mcp-demo && go get github.com/modelcontextprotocol/go-sdk/mcp
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
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type Response struct {
	Message string `json:"message"`
}

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
