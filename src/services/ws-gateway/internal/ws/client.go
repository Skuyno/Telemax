package ws

import (
	"encoding/json"
	"log"
	"time"

	"github.com/gorilla/websocket"
)

const (
	writeWait            = 10 * time.Second
	pongWait             = 60 * time.Second
	pingPeriod           = (pongWait * 9) / 10
	maxMessageSize       = 512
	presenceSyncCooldown = 5 * time.Second
)

type InboundCommand struct {
	Type string `json:"type"`
}

type Client struct {
	hub              *Hub
	userID           string
	conn             *websocket.Conn
	send             chan []byte
	lastPresenceSync time.Time
}

func NewClient(hub *Hub, userID string, conn *websocket.Conn) *Client {
	return &Client{
		hub:    hub,
		userID: userID,
		conn:   conn,
		send:   make(chan []byte, 256),
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
		messageType, data, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(
				err,
				websocket.CloseGoingAway,
				websocket.CloseAbnormalClosure,
			) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		if messageType != websocket.TextMessage {
			continue
		}

		var command InboundCommand
		if err := json.Unmarshal(data, &command); err != nil {
			log.Printf(
				"Invalid WebSocket command: user=%s error=%v",
				c.userID,
				err,
			)
			continue
		}

		switch command.Type {
		case "presence.sync":
			if time.Since(c.lastPresenceSync) < presenceSyncCooldown {
				continue
			}

			c.lastPresenceSync = time.Now()
			go c.hub.sendPresenceSnapshot(c)

		default:
			log.Printf(
				"Unknown WebSocket command: user=%s type=%q",
				c.userID,
				command.Type,
			)
		}
	}
}

func (c *Client) WritePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))

			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := c.conn.WriteMessage(websocket.TextMessage, message); err != nil {
				return
			}

		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))

			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
