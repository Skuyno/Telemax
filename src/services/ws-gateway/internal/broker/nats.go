package broker

import (
	"fmt"
	"log"

	"github.com/nats-io/nats.go"
)

type Client struct {
	nc *nats.Conn
	js nats.JetStreamContext
}

func New(natsUrl string) (*Client, error) {
	nc, err := nats.Connect(natsUrl)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to initialize JetStream: %w", err)
	}

	return &Client{
		nc: nc,
		js: js,
	}, nil
}

func (c *Client) SubscribeToMessages(subject string, handler func(data []byte)) (*nats.Subscription, error) {
	sub, err := c.js.Subscribe(subject, func(msg *nats.Msg) {
		log.Printf("Received NATS message on %s", msg.Subject)

		handler(msg.Data)

		msg.Ack()
	})

	if err != nil {
		return nil, fmt.Errorf("failed to subscribe to %s: %w", subject, err)
	}

	return sub, nil
}

func (c *Client) Close() {
	if c.nc != nil {
		c.nc.Close()
	}
}
