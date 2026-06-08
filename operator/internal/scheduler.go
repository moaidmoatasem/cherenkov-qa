package internal

import (
	"sync"
	"sync/atomic"
)

type Scheduler struct {
	mu            sync.Mutex
	inflight      int32
	maxConcurrent int32
}

func NewScheduler(maxConcurrent int32) *Scheduler {
	if maxConcurrent < 1 {
		maxConcurrent = 2
	}
	return &Scheduler{maxConcurrent: maxConcurrent}
}

func (s *Scheduler) TryAcquire() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.inflight < s.maxConcurrent {
		s.inflight++
		return true
	}
	return false
}

func (s *Scheduler) Release() {
	atomic.AddInt32(&s.inflight, -1)
}

func (s *Scheduler) Inflight() int32 {
	return atomic.LoadInt32(&s.inflight)
}

func (s *Scheduler) MaxConcurrent() int32 {
	return s.maxConcurrent
}
