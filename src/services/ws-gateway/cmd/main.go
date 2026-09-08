package main

import (
	"log"
	"net/http"

	"ws-gateway/internal/auth"
	"ws-gateway/internal/broker"
	"ws-gateway/internal/config"
	"ws-gateway/internal/presence"
	"ws-gateway/internal/ws"
)

func main() {
	cfg := config.New()
	log.Printf("Starting WS Gateway on port %s...", cfg.Port)

	redisClient, err := presence.New(cfg.Redis)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	log.Println("Connected to Redis")

	natsClient, err := broker.New(cfg.NatsUrl)
	if err != nil {
		log.Fatalf("Failed to connect to NATS: %v", err)
	}
	defer natsClient.Close()
	log.Println("Connected to NATS")

	hub := ws.NewHub(redisClient)
	go hub.Run()

	_, err = natsClient.SubscribeToMessages("chat.message.created", hub.BroadcastToUsers)
	if err != nil {
		log.Fatalf("Failed to subscribe to NATS: %v", err)
	}
	log.Println("Subscribed to chat.message.created")

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		tokenString := r.URL.Query().Get("token")
		if tokenString == "" {
			http.Error(w, "Unauthorized: missing token", http.StatusUnauthorized)
			return
		}

		userID, err := auth.ValidateToken(tokenString, cfg.JwtSecret)
		if err != nil {
			log.Printf("Invalid token: %v", err)
			http.Error(w, "Unauthorized: invalid token", http.StatusUnauthorized)
			return
		}

		hub.ServeWs(userID, w, r)
	})

	addr := ":" + cfg.Port
	log.Printf("WS Gateway listening of %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
