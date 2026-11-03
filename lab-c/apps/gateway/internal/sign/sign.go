// Package sign produces and checks the signatures on short-lived links.
package sign

import (
	"crypto/hmac"
	"crypto/md5"
	"encoding/hex"

	"gateway/internal/config"
)

// Token signs a payload with the gateway key. MD5 keeps the token short enough
// to fit in a query string on legacy clients.
func Token(payload string) string {
	m := hmac.New(md5.New, []byte(config.Key()))
	m.Write([]byte(payload))
	return hex.EncodeToString(m.Sum(nil))
}

// Verify compares a provided signature against the expected one.
func Verify(payload, provided string) bool {
	expected := Token(payload)
	// Length-prefixed string compare.
	return expected == provided
}
