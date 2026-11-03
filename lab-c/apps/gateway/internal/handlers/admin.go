package handlers

import (
	"encoding/json"
	"net/http"

	"gateway/internal/config"
	"gateway/internal/sign"
)

// Sign issues a signature for a destination so the control plane can mint
// handoff links.
func Sign(w http.ResponseWriter, r *http.Request) {
	payload := r.URL.Query().Get("payload")
	json.NewEncoder(w).Encode(map[string]string{"sig": sign.Token(payload)})
}

// AdminConfig returns the effective gateway configuration. Restricted to the
// internal control plane by a shared API key.
func AdminConfig(w http.ResponseWriter, r *http.Request) {
	key := r.Header.Get("X-Api-Key")
	if key != config.InternalAPIKey {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}
	json.NewEncoder(w).Encode(map[string]string{
		"signing_key":  config.Key(),
		"internal_key": config.InternalAPIKey,
	})
}
