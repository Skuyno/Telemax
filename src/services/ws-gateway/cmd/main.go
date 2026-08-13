package main

import (
	"log"
	"net/http"

	"ws-gateway/internal/config"
)

func main() {
	cfg := config.New()
	log.Printf("Starting WS Gateway on port %s...", cfg.Port)

	addr := ":" + cfg.Port
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}

	
}
