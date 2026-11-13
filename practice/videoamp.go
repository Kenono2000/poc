// Package documentation
// This file implements a self‑contained demonstration of several concurrent
// patterns and utilities commonly needed in production Go services:
//   * Multi‑tenant token‑bucket rate limiting
//   * Sliding‑window deduplication of impression events
//   * A background janitor that evicts stale state
//   * A mock LLM agent loop with tool fan‑out
//   * A bounded worker pool with back‑pressure handling
//   * A lock‑free map‑reduce style stream aggregator
// The `runDemo` function wires everything together and prints a concise report.

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"sort"
	"strings"
	"sync"
	"time"
)

// ============================================================================
// 1. SENTINEL ERRORS & DATA MODELS
// ============================================================================
// Define reusable sentinel errors that callers can compare using errors.Is.
var (
	ErrMaxTurns        = errors.New("agent exceeded maximum turn budget") // agent ran out of turns
	ErrQueueFull       = errors.New("worker queue saturated: backpressure")   // worker pool back‑pressure
	ErrPoolClosed      = errors.New("worker pool closed")                     // submit after shutdown
	ErrShutdownTimeout = errors.New("worker pool shutdown timed out")        // graceful shutdown timed out
)

// ImpressionEvent represents a single ad impression. The JSON tags ensure proper
// marshaling/unmarshaling when used over HTTP.
type ImpressionEvent struct {
	DeviceID   string    `json:"device_id"`
	CampaignID string    `json:"campaign_id"`
	Timestamp  time.Time `json:"timestamp"`
}

// SpendEvent is used for the aggregation demo – it records how many cents a
// campaign has spent.
type SpendEvent struct {
	CampaignID string
	SpendCents int64
}

// ToolCall describes a request by the LLM to invoke a tool.
type ToolCall struct {
	ID   string
	Name string
	Args map[string]any
}

// Message models a chat message. Depending on Role it may contain a tool call or
// a plain textual response.
type Message struct {
	Role       string // "user", "assistant", "tool"
	Content    string
	ToolCalls  []ToolCall
	ToolCallID string // populated when a tool response is added to history
}

// LLMClient abstracts a language model capable of generating the next message.
type LLMClient interface {
	Complete(ctx context.Context, history []Message) (Message, error)
}

// ToolExecutor abstracts a set of executable tools that the agent can call.
type ToolExecutor interface {
	Execute(ctx context.Context, name string, args map[string]any) (string, error)
}

// ============================================================================
// 2. MULTI‑TENANT TOKEN‑BUCKET RATE LIMITER (DOUBLE‑CHECKED LOCKING)
// ============================================================================
// Each tenant gets its own token bucket. Tokens are replenished at `rate`
// tokens/second up to `capacity`. The implementation lazily creates a bucket on
// first use and evicts idle buckets via the janitor.

type tokenBucket struct {
	mu         sync.Mutex // protects bucket fields
	tokens     float64    // current token count (allow fractional tokens)
	lastRefill time.Time  // last time tokens were added
	lastAccess time.Time  // last time bucket was used (for idle cleanup)
}

type TenantLimiter struct {
	mu          sync.RWMutex                // guards the map of buckets
	buckets     map[string]*tokenBucket     // tenant‑id → bucket
	rate        float64                     // refill rate (tokens per second)
	capacity    float64                     // maximum tokens that can accumulate
	idleTimeout time.Duration               // duration after which idle buckets are removed
}

func NewTenantLimiter(rate, capacity float64, idleTimeout time.Duration) *TenantLimiter {
	return &TenantLimiter{
		buckets:     make(map[string]*tokenBucket),
		rate:        rate,
		capacity:    capacity,
		idleTimeout: idleTimeout,
	}
}

// Allow attempts to consume `cost` tokens for the given tenant. It returns true
// if the bucket had enough tokens, otherwise false.
func (l *TenantLimiter) Allow(tenantID string, cost float64) bool {
	// Fast path: read‑lock to check existence.
	l.mu.RLock()
	tb, ok := l.buckets[tenantID]
	l.mu.RUnlock()
	if !ok {
		// Slow path: create bucket under write lock.
		l.mu.Lock()
		if tb, ok = l.buckets[tenantID]; !ok {
			now := time.Now()
			tb = &tokenBucket{tokens: l.capacity, lastRefill: now, lastAccess: now}
			l.buckets[tenantID] = tb
		}
		l.mu.Unlock()
	}
	// Refill and consume under bucket lock.
	tb.mu.Lock()
	defer tb.mu.Unlock()
	now := time.Now()
	tb.tokens += now.Sub(tb.lastRefill).Seconds() * l.rate
	if tb.tokens > l.capacity {
		tb.tokens = l.capacity
	}
	tb.lastRefill = now
	tb.lastAccess = now
	if tb.tokens >= cost {
		tb.tokens -= cost
		return true
	}
	return false
}

// ============================================================================
// 3. SLIDING‑WINDOW DEDUPLICATOR & BACKGROUND JANITOR
// ============================================================================
// Deduplicator drops impression events that arrive within `window` for the same
// (device, campaign) pair. It also keeps a simple per‑campaign reach count.

type Deduplicator struct {
	mu     sync.RWMutex               // guards internal maps
	window time.Duration              // minimum interval between duplicate events
	seen   map[string]time.Time       // key → timestamp of last seen event
	reach  map[string]int64           // campaign → unique impression count
}

func NewDeduplicator(window time.Duration) *Deduplicator {
	return &Deduplicator{
		window: window,
		seen:   make(map[string]time.Time),
		reach:  make(map[string]int64),
	}
}

// Ingest returns true if the event is new (not a duplicate within the window).
func (d *Deduplicator) Ingest(e ImpressionEvent) bool {
	key := e.DeviceID + ":" + e.CampaignID
	d.mu.Lock()
	defer d.mu.Unlock()
	if last, ok := d.seen[key]; ok && e.Timestamp.Sub(last) < d.window {
		return false // duplicate – drop it
	}
	d.seen[key] = e.Timestamp
	d.reach[e.CampaignID]++
	return true
}

// StartJanitor runs a periodic goroutine that removes stale token buckets and
// expired deduplication entries.
func StartJanitor(ctx context.Context, interval time.Duration, limiter *TenantLimiter, dedup *Deduplicator) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				now := time.Now()
				// Clean idle token buckets.
				limiter.mu.Lock()
				for id, tb := range limiter.buckets {
					tb.mu.Lock()
					idle := now.Sub(tb.lastAccess)
					tb.mu.Unlock()
					if idle > limiter.idleTimeout {
						delete(limiter.buckets, id)
					}
				}
				limiter.mu.Unlock()
				// Clean expired dedup entries.
				dedup.mu.Lock()
				for k, ts := range dedup.seen {
					if now.Sub(ts) > dedup.window {
						delete(dedup.seen, k)
					}
				}
				dedup.mu.Unlock()
			}
		}
	}()
}

// IngestHandler validates the tenant header, applies rate limiting, decodes the
// JSON payload, and forwards the impression to the deduplicator. It returns a
// JSON payload indicating whether the event was accepted.
func IngestHandler(limiter *TenantLimiter, dedup *Deduplicator) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		tenantID := r.Header.Get("X-Tenant-ID")
		if tenantID == "" {
			http.Error(w, "missing X-Tenant-ID", http.StatusUnauthorized)
			return
		}
		if !limiter.Allow(tenantID, 1.0) {
			http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
			return
		}
		var event ImpressionEvent
		dec := json.NewDecoder(r.Body)
		dec.DisallowUnknownFields()
		if err := dec.Decode(&event); err != nil || event.DeviceID == "" || event.CampaignID == "" {
			http.Error(w, "invalid JSON payload", http.StatusBadRequest)
			return
		}
		if event.Timestamp.IsZero() {
			event.Timestamp = time.Now()
		}
		accepted := dedup.Ingest(event)
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{"accepted": accepted, "tenant_id": tenantID})
	}
}

// ============================================================================
// 4. AGENT RUNNER LOOP & CONCURRENT TOOL FAN‑OUT
// ============================================================================
// The AgentRunner coordinates a simple LLM interaction. It feeds the LLM the
// conversation history, collects any requested tool calls, runs those tools in
// parallel (each with a timeout), and appends the tool results back into the
// conversation for the next turn.

type AgentRunner struct {
	llm         LLMClient
	tools       ToolExecutor
	maxTurns    int           // safety guard to prevent infinite loops
	toolTimeout time.Duration // per‑tool execution deadline
}

func (a *AgentRunner) Run(ctx context.Context, prompt string) (string, error) {
	history := []Message{{Role: "user", Content: prompt}}
	for turn := 0; turn < a.maxTurns; turn++ {
		if err := ctx.Err(); err != nil {
			return "", fmt.Errorf("agent cancelled at turn %d: %w", turn, err)
		}
		reply, err := a.llm.Complete(ctx, history)
		if err != nil {
			return "", fmt.Errorf("llm completion failed at turn %d: %w", turn, err)
		}
		history = append(history, reply)
		if len(reply.ToolCalls) == 0 {
			return reply.Content, nil // final response – no more tool calls
		}
		// Execute each tool concurrently and collect results.
		results := make([]Message, len(reply.ToolCalls))
		var wg sync.WaitGroup
		for i, tc := range reply.ToolCalls {
			wg.Add(1)
			go func(idx int, call ToolCall) {
				defer wg.Done()
				tCtx, cancel := context.WithTimeout(ctx, a.toolTimeout)
				defer cancel()
				out, err := a.tools.Execute(tCtx, call.Name, call.Args)
				if err != nil {
					out = fmt.Sprintf("tool %s error: %v", call.Name, err)
				}
				results[idx] = Message{Role: "tool", Content: out, ToolCallID: call.ID}
			}(i, tc)
		}
		wg.Wait()
		history = append(history, results...)
	}
	return "", fmt.Errorf("run aborted: %w", ErrMaxTurns)
}

// ============================================================================
// 5. BOUNDED WORKER POOL WITH BACKPRESSURE & DRAIN
// ============================================================================
// WorkerPool maintains a fixed set of goroutine workers that pull jobs from a
// buffered channel. Submitting when the channel is full returns ErrQueueFull –
// this provides natural back‑pressure for callers.

type WorkerPool struct {
	jobs   chan func(ctx context.Context) error
	wg     sync.WaitGroup
	mu     sync.Mutex
	closed bool
}

func NewWorkerPool(workers, queueDepth int, taskTimeout time.Duration) *WorkerPool {
	wp := &WorkerPool{jobs: make(chan func(context.Context) error, queueDepth)}
	for i := 0; i < workers; i++ {
		wp.wg.Add(1)
		go func() {
			defer wp.wg.Done()
			for job := range wp.jobs {
				// Each job runs with an individual timeout context.
				tCtx, cancel := context.WithTimeout(context.Background(), taskTimeout)
				_ = job(tCtx)
				cancel()
			}
		}()
	}
	return wp
}

func (wp *WorkerPool) Submit(job func(ctx context.Context) error) error {
	wp.mu.Lock()
	defer wp.mu.Unlock()
	if wp.closed {
		return ErrPoolClosed
	}
	select {
	case wp.jobs <- job:
		return nil
	default:
		return ErrQueueFull
	}
}

func (wp *WorkerPool) Shutdown(timeout time.Duration) error {
	wp.mu.Lock()
	if wp.closed {
		wp.mu.Unlock()
		return nil
	}
	wp.closed = true
	close(wp.jobs)
	wp.mu.Unlock()
	done := make(chan struct{})
	go func() {
		wp.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
		return nil
	case <-time.After(timeout):
		return ErrShutdownTimeout
	}
}

// ============================================================================
// 6. LOCK‑FREE STREAM AGGREGATOR (MAP‑REDUCE) & TABLE RACE TEST
// ============================================================================
// AggregateStream distributes SpendEvent values across `workers` goroutines. Each
// worker builds a local map of campaign → spend and once all workers finish the
// partial maps are merged into a final result. This approach avoids shared‑state
// contention during the heavy aggregation loop.
func AggregateStream(ctx context.Context, stream <-chan SpendEvent, workers int) (map[string]int64, error) {
	if workers <= 0 {
		workers = 1
	}
	results := make(chan map[string]int64, workers)
	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			local := make(map[string]int64)
			for {
				select {
				case <-ctx.Done():
					return
				case ev, ok := <-stream:
					if !ok {
						results <- local
						return
					}
					local[ev.CampaignID] += ev.SpendCents
				}
			}
		}()
	}
	go func() {
		wg.Wait()
		close(results)
	}()
	final := make(map[string]int64)
	for partial := range results {
		for k, v := range partial {
			final[k] += v
		}
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return final, nil
}

// ---------------------------------------------------------------------------
// Demo implementations used by runDemo (mock LLM + mock tool).
// ---------------------------------------------------------------------------

type demoLLM struct {
	turn int // tracks which turn we are on
}

func (d *demoLLM) Complete(ctx context.Context, history []Message) (Message, error) {
	if err := ctx.Err(); err != nil {
		return Message{}, err
	}
	// On the first turn we ask the agent to call the "uppercase" tool.
	if d.turn == 0 {
		d.turn++
		return Message{
			Role: "assistant",
			ToolCalls: []ToolCall{{
				ID:   "tool-1",
				Name: "uppercase",
				Args: map[string]any{"value": "hello from the agent"},
			}},
		}, nil
	}
	// Subsequent turn returns a plain textual reply.
	return Message{Role: "assistant", Content: "agent finished after tool execution"}, nil
}

type demoToolExecutor struct{}

func (demoToolExecutor) Execute(ctx context.Context, name string, args map[string]any) (string, error) {
	if err := ctx.Err(); err != nil {
		return "", err
	}
	switch name {
	case "uppercase":
		value, _ := args["value"].(string)
		return strings.ToUpper(value), nil
	default:
		return fmt.Sprintf("%s:%v", name, args), nil
	}
}

// postIngestEvent posts a single impression to the HTTP ingest endpoint and
// returns the "accepted" flag from the JSON response.
func postIngestEvent(ctx context.Context, client *http.Client, url, tenantID string, event ImpressionEvent) (bool, error) {
	body, err := json.Marshal(event)
	if err != nil {
		return false, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return false, err
	}
	req.Header.Set("X-Tenant-ID", tenantID)
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("unexpected status %s", resp.Status)
	}
	var payload map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return false, err
	}
	accepted, _ := payload["accepted"].(bool)
	return accepted, nil
}

// runDemo wires together all components, exercises them, and prints a short
// report. Errors are propagated to the caller.
func runDemo(ctx context.Context) error {
	limiter := NewTenantLimiter(5, 10, 30*time.Second) // 5 req/s, burst up to 10
	dedup := NewDeduplicator(2 * time.Minute)        // dedupe window of 2 minutes

	janitorCtx, cancelJanitor := context.WithCancel(ctx)
	defer cancelJanitor()
	StartJanitor(janitorCtx, 25*time.Millisecond, limiter, dedup)

	server := httptest.NewServer(IngestHandler(limiter, dedup))
	defer server.Close()

	// Send two identical events to demonstrate deduplication.
	event := ImpressionEvent{DeviceID: "device-1", CampaignID: "campaign-1", Timestamp: time.Now().UTC()}
	client := &http.Client{Timeout: 2 * time.Second}
	acceptedFirst, err := postIngestEvent(ctx, client, server.URL, "tenant-a", event)
	if err != nil {
		return fmt.Errorf("first ingest: %w", err)
	}
	acceptedSecond, err := postIngestEvent(ctx, client, server.URL, "tenant-a", event)
	if err != nil {
		return fmt.Errorf("second ingest: %w", err)
	}

	// Aggregate a small stream of spend events.
	spendStream := make(chan SpendEvent, 3)
	spendStream <- SpendEvent{CampaignID: "campaign-1", SpendCents: 100}
	spendStream <- SpendEvent{CampaignID: "campaign-2", SpendCents: 250}
	spendStream <- SpendEvent{CampaignID: "campaign-1", SpendCents: 50}
	close(spendStream)
	totals, err := AggregateStream(ctx, spendStream, 2)
	if err != nil {
		return fmt.Errorf("aggregate stream: %w", err)
	}

	// Demonstrate the bounded worker pool.
	pool := NewWorkerPool(2, 4, time.Second)
	var poolMu sync.Mutex
	completed := make([]string, 0, 2)
	for _, label := range []string{"alpha", "beta"} {
		label := label // capture loop variable
		if err := pool.Submit(func(jobCtx context.Context) error {
			if err := jobCtx.Err(); err != nil {
				return err
			}
			poolMu.Lock()
			completed = append(completed, label)
			poolMu.Unlock()
			return nil
		}); err != nil {
			return fmt.Errorf("submit worker job: %w", err)
		}
	}
	if err := pool.Shutdown(2 * time.Second); err != nil {
		return fmt.Errorf("shutdown worker pool: %w", err)
	}
	sort.Strings(completed)

	// Run the mock LLM agent.
	runner := &AgentRunner{llm: &demoLLM{}, tools: demoToolExecutor{}, maxTurns: 3, toolTimeout: time.Second}
	agentReply, err := runner.Run(ctx, "demonstrate the agent loop")
	if err != nil {
		return fmt.Errorf("agent run: %w", err)
	}

	// Print results.
	fmt.Println("Production Go Systems Script")
	fmt.Printf("ingest accepted=%v duplicate accepted=%v\n", acceptedFirst, acceptedSecond)
	fmt.Printf("aggregate totals=%v\n", totals)
	fmt.Printf("worker pool completed=%v\n", completed)
	fmt.Printf("agent reply=%q\n", agentReply)
	return nil
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := runDemo(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "script failed: %v\n", err)
		os.Exit(1)
	}
}
