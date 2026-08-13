package presence

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type Client struct {
	rdb *redis.Client
}

func New(redisURL string) (*Client, error) {
	rdb := redis.NewClient(&redis.Options {
		Addr: redisURL,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to redis: %w", err)
	}

	return &Client{rdb: rdb}, nil
}

func (c *Client) SetOnline(ctx context.Context, userID string, expiration time.Duration) error {
	key := fmt.Sprintf("user:%s:online", userID)
	return c.rdb.Set(ctx, key, "true", expiration).Err()
}

func (c *Client) SetOffline(ctx context.Context, userID string) error {
	key := fmt.Sprintf("user:%s:online", userID)
	return c.rdb.Del(ctx, key).Err()
}