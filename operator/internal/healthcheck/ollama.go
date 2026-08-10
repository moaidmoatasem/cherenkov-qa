// Package healthcheck provides health and readiness probe checkers for external services.
package healthcheck

import (
	"fmt"
	"net/http"
)

// OllamaReadyz checks whether the local Ollama LLM provider service is active and ready.
func OllamaReadyz(req *http.Request) error {
	resp, err := http.Get("http://localhost:11434/api/tags")
	if err != nil || resp.StatusCode != 200 {
		return fmt.Errorf("ollama not ready")
	}
	return nil
}
