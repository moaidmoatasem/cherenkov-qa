package healthcheck

import (
	"fmt"
	"net/http"
)

func OllamaReadyz(req *http.Request) error {
	resp, err := http.Get("http://localhost:11434/api/tags")
	if err != nil || resp.StatusCode != 200 {
		return fmt.Errorf("ollama not ready")
	}
	return nil
}
