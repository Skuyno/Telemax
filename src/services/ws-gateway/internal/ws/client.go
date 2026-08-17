package ws

import (
	"context"
	"log"
	"time"

	"ws-gateway/internal/presence"

	"github.com/gorilla/websocket"
)

const (
	// Время, отведенное на запись сообщения клиенту
	writeWait = 10 * time.Second
	// Время ожидания ответа Pong от клиента (heartbeat)
	pongWait = 60 * time.Second
	// Периодичность отправки Ping клиенту (должна быть меньше pongWait)
	pingPeriod = (pongWait * 9) / 10
	// Максимальный размер входящего сообщения
	maxMessageSize = 512
)

type Client struct {
	hub      *Hub
	userID   string
	conn     *websocket.Conn
	send     chan []byte
	presence *presence.Client
}

func NewClient(hub *Hub, userID string, conn *websocket.Conn, presence *presence.Client) *Client {
	return &Client{
		hub:      hub,
		userID:   userID,
		conn:     conn,
		send:     make(chan []byte, 256),
		presence: presence,
	}
}

func (c *Client) ReadPump() {
	defer func() {
		c.hub.unregister <- c
		c.conn.Close()
		_ = c.presence.SetOffline(context.Background(), c.userID)
	}()

	c.conn.SetReadLimit(maxMessageSize)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
		_ = c.presence.SetOnline(context.Background(), c.userID, 70*time.Second)
		return nil
	})

	for {
		_, _, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}
	}
}

func (c *Client) WritePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func () {
		ticker.Stop()
		c.conn.Close()
	} ()

	for {
		select{
		case message, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			_, _ = w.Write(message)

			n := len(c.send)
			for i := 0; i < n; i++ {
				_, _ = w.Write([]byte{'\n'})
				_, _ = w.Write(<-c.send)
			}

			if err := w.Close(); err != nil {
				return
			}
		case <- ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
