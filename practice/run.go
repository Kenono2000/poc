package main

import (
	"context"
	"fmt"
	"sync"
	"time"
)
func process(t string) string {
	return "done: " + t
}
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
func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	tasks := []string{"alpha", "beta", "gamma"}
	results := RunAll(ctx, tasks)
	fmt.Println("Results:")
	for i, res := range results {
		fmt.Printf("[%d] %s\n", i, res)
	}
}
