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

const (
	presenceTTL     = 70 * time.Second
	presenceTimeout = 2 * time.Second
)

type InboundEvent struct {
	ID           string   `json:"id"`
	ChatID       string   `json:"chat_id"`
	SenderID     string   `json:"sender_id"`
	RecipientIDs []string `json:"recipient_ids"`
	Body         string   `json:"body"`
	CreatedAt    string   `json:"created_at"`
}

type MessageData struct {
	MessageID string `json:"message_id"`
	ChatID    string `json:"chat_id"`
	SenderID  string `json:"sender_id"`
	Body      string `json:"body"`
	CreatedAt string `json:"created_at"`
}

type MessageCreatedEvent struct {
	Type string      `json:"type"`
	Data MessageData `json:"data"`
}

type Hub struct {
	presence *presence.Client
	users    map[string]map[*Client]struct{}
	mu       sync.RWMutex

	register   chan *Client
	unregister chan *Client
	heartbeat  chan *Client
}

func NewHub(presenceClient *presence.Client) *Hub {
	return &Hub{
		presence:   presenceClient,
		users:      make(map[string]map[*Client]struct{}),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		heartbeat:  make(chan *Client),
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
			count := len(h.users[client.userID])

			h.mu.Unlock()
			h.updatePresence(client.userID, true)
			log.Printf(
				"Client connected: user=%s (total connections: %d)",
				client.userID, count,
			)
		case client := <-h.unregister:
			lastConnection := false
			h.mu.Lock()
			if connections, ok := h.users[client.userID]; ok {
				if _, exists := connections[client]; exists {
					delete(connections, client)
					close(client.send)
					if len(connections) == 0 {
						delete(h.users, client.userID)
						lastConnection = true
					}
				}
			}
			h.mu.Unlock()

			if lastConnection {
				h.updatePresence(client.userID, false)
			}
			log.Printf("Client disconnected: user=%s", client.userID)
		case client := <-h.heartbeat:
			h.mu.RLock()
			_, connected := h.users[client.userID][client]
			h.mu.RUnlock()

			if connected {
				h.updatePresence(client.userID, true)
			}
		}

	}
}

func (h *Hub) updatePresence(userID string, online bool) {
	ctx, cancel := context.WithTimeout(
		context.Background(),
		presenceTimeout,
	)
	defer cancel()

	var err error
	if online {
		err = h.presence.SetOnline(ctx, userID, presenceTTL)
	} else {
		err = h.presence.SetOffline(ctx, userID)
	}

	if err != nil {
		log.Printf(
			"Failed to update presence: user=%s online=%t error=%v",
			userID, online, err,
		)
	}
}

func (h *Hub) BroadcastToUsers(data []byte) {
	var event InboundEvent
	if err := json.Unmarshal(data, &event); err != nil {
		log.Printf("Failed to parse inbound NATS event: %v", err)
		return
	}

	outgoing := MessageCreatedEvent{
		Type: "message.created",
		Data: MessageData{
			MessageID: event.ID,
			ChatID:    event.ChatID,
			SenderID:  event.SenderID,
			Body:      event.Body,
			CreatedAt: event.CreatedAt,
		},
	}

	payload, err := json.Marshal(outgoing)
	if err != nil {
		log.Printf("Failed to encode WebSocket event: %v", err)
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	for _, recipientID := range event.RecipientIDs {
		if connections, ok := h.users[recipientID]; ok {
			for client := range connections {
				select {
				case client.send <- payload:
				default:
					log.Printf(
						"Client buffer full, dropping message for user=%s",
						recipientID,
					)
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

func (h *Hub) ServeWs(userID string, w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}

	client := NewClient(h, userID, conn)
	h.register <- client

	go client.WritePump()
	go client.ReadPump()
}
