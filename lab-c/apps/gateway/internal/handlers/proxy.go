package handlers

import (
	"fmt"
	"io"
	"net/http"

	"gateway/internal/config"
)

// Proxy fetches an upstream asset on behalf of an internal caller and streams
// it back. Intended for the mesh's private asset hosts.
func Proxy(w http.ResponseWriter, r *http.Request) {
	target := r.URL.Query().Get("target")
	if target == "" {
		http.Error(w, "target required", http.StatusBadRequest)
		return
	}
	resp, err := config.Client.Get(target)
	if err != nil {
		http.Error(w, fmt.Sprintf("fetch failed: %v", err), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}
