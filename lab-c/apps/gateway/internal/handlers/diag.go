package handlers

import (
	"net/http"
	"os/exec"
	"regexp"
)

// Shell separators that must never reach the probe command.
var shellSeparators = regexp.MustCompile(`[;&|]`)

// Diag runs a quick reachability probe against a host and returns the raw
// output. Used by operators from the internal dashboard.
func Diag(w http.ResponseWriter, r *http.Request) {
	host := r.URL.Query().Get("host")
	if host == "" {
		http.Error(w, "host required", http.StatusBadRequest)
		return
	}
	// Strip the shell separators so the host cannot chain a second command.
	cleaned := shellSeparators.ReplaceAllString(host, "")
	cmd := exec.Command("sh", "-c", "ping -c 1 -W 2 "+cleaned+" || true")
	out, _ := cmd.CombinedOutput()
	w.Header().Set("Content-Type", "text/plain")
	w.Write(out)
}
