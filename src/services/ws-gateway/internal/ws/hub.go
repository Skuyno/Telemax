package ws

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"
	"ws-gateway/internal/presence"

	"github.com/gorilla/websocket"
)

type InboundEvent struct {
	Type         string          `json:"type"`
	RecipientIDs []string        `json:"recipient_ids"`
	Payload      json.RawMessage `json:"payload"`
}

type Hub struct {
	users map[string]map[*Client]struct{}

	mu sync.RWMutex

	register   chan *Client
	unregister chan *Client
}

func NewHub() *Hub {
	return &Hub{
		users:      make(map[string]map[*Client]struct{}),
		register:   make(chan *Client),
		unregister: make(chan *Client),
	}
}

func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			if _, ok := h.users[client.userID]; !ok {
				h.users[client.userID] = make(map[*Client]struct{})
			}
			h.users[client.userID][client] = struct{}{}
			h.mu.Unlock()
			log.Printf("Client connected: user=%s (total connections: %d)", client.userID, len(h.users[client.userID]))
		case client := <-h.unregister:
			h.mu.Lock()
			if connections, ok := h.users[client.userID]; ok {
				if _, exists := connections[client]; exists {
					delete(connections, client)
					close(client.send)
					if len(connections) == 0 {
						delete(h.users, client.userID)
					}
				}
			}
			h.mu.Unlock()
			log.Printf("Client disconnected: user=%s", client.userID)
		}

	}
}

func (h *Hub) BroadcastToUsers(data []byte) {
	var event InboundEvent
	if err := json.Unmarshal(data, &event); err != nil {
		log.Printf("Failed to parse inbound NATS event: %v", err)
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	for _, recipientID := range event.RecipientIDs {
		if connections, ok := h.users[recipientID]; ok {
			for client := range connections {
				select {
				case client.send <- data:
				default:
					log.Printf("Client buffer full, dropping message for user=%s", recipientID)
				}
			}
		}

	}
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

func (h *Hub) ServeWs(presenceClient *presence.Client, userID string, w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}

	client := NewClient(h, userID, conn, presenceClient)

	h.register <- client

	_ = presenceClient.SetOnline(context.Background(), userID, 70*time.Second)

	go client.WritePump()
	go client.ReadPump()
}
