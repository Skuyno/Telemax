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

	subjectMessageCreated = "chat.message.created"
	subjectMessageUpdated = "chat.message.updated"
	subjectMessageDeleted = "chat.message.deleted"
	subjectMessageRead    = "chat.message.read"
	subjectTyping         = "chat.message.typing"

	subjectUploadProgress  = "file.upload.progress"
	subjectUploadCompleted = "file.upload.completed"
)

// InboundEvent is a superset of the fields any chat.message.* event from
// communication might carry. Fields irrelevant to a given subject are left
// as zero values by json.Unmarshal, not an error.
type InboundEvent struct {
	ID                string   `json:"id"`
	ChatID            string   `json:"chat_id"`
	SenderID          string   `json:"sender_id"`
	UserID            string   `json:"user_id"`
	RecipientIDs      []string `json:"recipient_ids"`
	Body              string   `json:"body"`
	CreatedAt         string   `json:"created_at"`
	EditedAt          string   `json:"edited_at"`
	LastReadMessageID string   `json:"last_read_message_id"`

	FileID        string `json:"file_id"`
	UploaderID    string `json:"uploader_id"`
	BytesUploaded int64  `json:"bytes_uploaded"`
	SizeBytes     *int64 `json:"size_bytes"`
}

type MessageData struct {
	MessageID string  `json:"message_id"`
	ChatID    string  `json:"chat_id"`
	SenderID  string  `json:"sender_id"`
	Body      string  `json:"body"`
	CreatedAt string  `json:"created_at"`
	EditedAt  *string `json:"edited_at,omitempty"`
}

type MessageDeletedData struct {
	MessageID string `json:"message_id"`
	ChatID    string `json:"chat_id"`
	SenderID  string `json:"sender_id"`
}

type MessageReadData struct {
	ChatID            string `json:"chat_id"`
	UserID            string `json:"user_id"`
	LastReadMessageID string `json:"last_read_message_id"`
}

type TypingData struct {
	ChatID string `json:"chat_id"`
	UserID string `json:"user_id"`
}

type UploadProgressData struct {
	FileID        string `json:"file_id"`
	ChatID        string `json:"chat_id"`
	UploaderID    string `json:"uploader_id"`
	BytesUploaded int64  `json:"bytes_uploaded"`
	SizeBytes     *int64 `json:"size_bytes"`
}

type UploadCompletedData struct {
	FileID     string `json:"file_id"`
	ChatID     string `json:"chat_id"`
	UploaderID string `json:"uploader_id"`
	SizeBytes  int64  `json:"size_bytes"`
}

// OutboundEvent is the envelope every WebSocket client receives, regardless
// of what kind of chat.message.* event triggered it.
type OutboundEvent struct {
	Type string      `json:"type"`
	Data interface{} `json:"data"`
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

// buildOutboundEvent maps a NATS subject + decoded payload to the envelope
// sent to WebSocket clients. Returns ok=false for a subject nothing here
// knows how to handle.
func buildOutboundEvent(subject string, event InboundEvent) (OutboundEvent, bool) {
	switch subject {
	case subjectMessageCreated:
		return OutboundEvent{
			Type: "message.created",
			Data: MessageData{
				MessageID: event.ID,
				ChatID:    event.ChatID,
				SenderID:  event.SenderID,
				Body:      event.Body,
				CreatedAt: event.CreatedAt,
			},
		}, true
	case subjectMessageUpdated:
		var editedAt *string
		if event.EditedAt != "" {
			editedAt = &event.EditedAt
		}
		return OutboundEvent{
			Type: "message.updated",
			Data: MessageData{
				MessageID: event.ID,
				ChatID:    event.ChatID,
				SenderID:  event.SenderID,
				Body:      event.Body,
				CreatedAt: event.CreatedAt,
				EditedAt:  editedAt,
			},
		}, true
	case subjectMessageDeleted:
		return OutboundEvent{
			Type: "message.deleted",
			Data: MessageDeletedData{
				MessageID: event.ID,
				ChatID:    event.ChatID,
				SenderID:  event.SenderID,
			},
		}, true
	case subjectMessageRead:
		return OutboundEvent{
			Type: "message.read",
			Data: MessageReadData{
				ChatID:            event.ChatID,
				UserID:            event.UserID,
				LastReadMessageID: event.LastReadMessageID,
			},
		}, true
	case subjectTyping:
		return OutboundEvent{
			Type: "typing",
			Data: TypingData{
				ChatID: event.ChatID,
				UserID: event.UserID,
			},
		}, true
	case subjectUploadProgress:
		return OutboundEvent{
			Type: "upload.progress",
			Data: UploadProgressData{
				FileID:        event.FileID,
				ChatID:        event.ChatID,
				UploaderID:    event.UploaderID,
				BytesUploaded: event.BytesUploaded,
				SizeBytes:     event.SizeBytes,
			},
		}, true
	case subjectUploadCompleted:
		var sizeBytes int64
		if event.SizeBytes != nil {
			sizeBytes = *event.SizeBytes
		}
		return OutboundEvent{
			Type: "upload.completed",
			Data: UploadCompletedData{
				FileID:     event.FileID,
				ChatID:     event.ChatID,
				UploaderID: event.UploaderID,
				SizeBytes:  sizeBytes,
			},
		}, true
	default:
		return OutboundEvent{}, false
	}
}

// HandleNatsEvent parses one chat.message.* event and relays it to the
// connections of every id in its recipient_ids, using the NATS subject
// (not the payload) to decide which WebSocket envelope type to send.
func (h *Hub) HandleNatsEvent(subject string, data []byte) {
	var event InboundEvent
	if err := json.Unmarshal(data, &event); err != nil {
		log.Printf("Failed to parse inbound NATS event on %s: %v", subject, err)
		return
	}

	outgoing, ok := buildOutboundEvent(subject, event)
	if !ok {
		log.Printf("Unknown NATS subject, dropping event: %s", subject)
		return
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
