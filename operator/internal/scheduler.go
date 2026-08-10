// Package internal provides job execution and scheduling mechanisms for the CHERENKOV operator.
package internal

import (
	"sync"
	"sync/atomic"
)

// Scheduler manages concurrency limits for LLM-assisted validation tasks.
type Scheduler struct {
	mu            sync.Mutex
	inflight      int32
	maxConcurrent int32
}

// NewScheduler initializes a Scheduler with the specified maximum concurrent task limit.
func NewScheduler(maxConcurrent int32) *Scheduler {
	if maxConcurrent < 1 {
		maxConcurrent = 2
	}
	return &Scheduler{maxConcurrent: maxConcurrent}
}

// TryAcquire attempts to reserve an execution slot, returning true if acquired.
func (s *Scheduler) TryAcquire() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.inflight < s.maxConcurrent {
		s.inflight++
		return true
	}
	return false
}

// Release decrements the count of active inflight tasks.
func (s *Scheduler) Release() {
	atomic.AddInt32(&s.inflight, -1)
}

// Inflight returns the current count of active inflight tasks.
func (s *Scheduler) Inflight() int32 {
	return atomic.LoadInt32(&s.inflight)
}

// MaxConcurrent returns the maximum configured concurrency limit.
func (s *Scheduler) MaxConcurrent() int32 {
	return s.maxConcurrent
}
