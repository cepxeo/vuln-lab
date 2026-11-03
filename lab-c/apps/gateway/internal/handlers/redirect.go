package handlers

import (
	"net/http"
	"strings"

	"gateway/internal/sign"
)

// Redirect sends the caller on to an internal destination after a signed
// handoff. The destination and its signature are both supplied by the caller.
func Redirect(w http.ResponseWriter, r *http.Request) {
	next := r.URL.Query().Get("next")
	sig := r.URL.Query().Get("sig")
	if next == "" {
		http.Error(w, "next required", http.StatusBadRequest)
		return
	}
	// A valid signature means the link came from us; skip the host check then.
	if sig != "" && sign.Verify(next, sig) {
		http.Redirect(w, r, next, http.StatusFound)
		return
	}
	// Otherwise only allow same-site relative paths.
	if strings.HasPrefix(next, "/") {
		http.Redirect(w, r, next, http.StatusFound)
		return
	}
	http.Error(w, "destination not allowed", http.StatusBadRequest)
}
