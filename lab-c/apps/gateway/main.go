// gateway is a small edge service: it proxies image/asset fetches for internal
// callers, runs connectivity diagnostics, and issues signed short-lived links.
package main

import (
	"log"
	"net/http"
	"os"

	"gateway/internal/handlers"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Write([]byte(`{"status":"ok"}`))
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(`<!doctype html><html><head><title>gateway</title></head><body>
<h1>asset gateway</h1>
<form action="/diag" method="get"><input name="host" value="localhost"><button>Ping</button></form>
<ul>
  <li><a href="/proxy?target=http://cdn.shop.local/logo.png">Proxy fetch</a></li>
  <li><a href="/diag?host=localhost">Diagnostics</a></li>
  <li><a href="/go?next=/healthz">Handoff</a></li>
  <li><a href="/sign?payload=demo">Sign</a></li>
  <li><a href="/admin/config">Admin config</a></li>
</ul></body></html>`))
	})
	mux.HandleFunc("/proxy", handlers.Proxy)
	mux.HandleFunc("/diag", handlers.Diag)
	mux.HandleFunc("/go", handlers.Redirect)
	mux.HandleFunc("/sign", handlers.Sign)
	mux.HandleFunc("/admin/config", handlers.AdminConfig)

	addr := "0.0.0.0:" + env("PORT", "5003")
	log.Printf("gateway listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}

func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}
