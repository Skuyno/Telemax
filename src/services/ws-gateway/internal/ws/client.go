package ws

import (
	"log"
	"time"

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
}

func NewClient(hub *Hub, userID string, conn *websocket.Conn) *Client {
	return &Client{
		hub:      hub,
		userID:   userID,
		conn:     conn,
		send:     make(chan []byte, 256),
	}
}

func (c *Client) ReadPump() {
	defer func() {
		c.conn.Close()
		c.hub.unregister <- c
	}()

	c.conn.SetReadLimit(maxMessageSize)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		if err := c.conn.SetReadDeadline(
			time.Now().Add(pongWait),
		); err != nil {
			return err
		}
		c.hub.heartbeat <- c
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

			if err := c.conn.WriteMessage(websocket.TextMessage, message); err != nil {
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
