package broker

import (
	"fmt"
	"log"
	"time"

	"github.com/nats-io/nats.go"
)

const (
	subscribeMaxAttempts = 15
	subscribeRetryDelay  = 2 * time.Second
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

// SubscribeToMessagesWithRetry retries the subscription while the target
// JetStream stream doesn't exist yet. The "CHATS" stream is created by the
// communication service on its own startup, not by ws-gateway, so on a cold
// start of the whole stack ws-gateway can come up first and hit a normal,
// expected race rather than a real failure.
func (c *Client) SubscribeToMessagesWithRetry(
	subject string, handler func(data []byte),
) (*nats.Subscription, error) {
	var lastErr error
	for attempt := 1; attempt <= subscribeMaxAttempts; attempt++ {
		sub, err := c.SubscribeToMessages(subject, handler)
		if err == nil {
			return sub, nil
		}
		lastErr = err
		log.Printf(
			"Subscribe to %s failed (attempt %d/%d): %v — retrying in %s",
			subject, attempt, subscribeMaxAttempts, err, subscribeRetryDelay,
		)
		time.Sleep(subscribeRetryDelay)
	}
	return nil, fmt.Errorf(
		"subscribe to %s failed after %d attempts: %w", subject, subscribeMaxAttempts, lastErr,
	)
}

func (c *Client) Close() {
	if c.nc != nil {
		c.nc.Close()
	}
}
