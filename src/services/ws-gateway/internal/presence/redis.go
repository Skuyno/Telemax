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
	rdb := redis.NewClient(&redis.Options{
		Addr:                  redisURL,
		ContextTimeoutEnabled: true,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to redis: %w", err)
	}

	return &Client{rdb: rdb}, nil
}

func onlineKey(userID string) string {
	return fmt.Sprintf("user:%s:online", userID)
}

func (c *Client) SetOnline(ctx context.Context, userID string, expiration time.Duration) error {
	return c.rdb.Set(ctx, onlineKey(userID), "true", expiration).Err()
}

func (c *Client) SetOffline(ctx context.Context, userID string) error {
	return c.rdb.Del(ctx, onlineKey(userID)).Err()
}

func (c *Client) GetStatuses(
	ctx context.Context,
	userIDs []string,
) (map[string]bool, error) {
	statuses := make(map[string]bool, len(userIDs))
	if len(userIDs) == 0 {
		return statuses, nil
	}

	keys := make([]string, len(userIDs))
	for i, userID := range userIDs {
		keys[i] = onlineKey(userID)
	}

	values, err := c.rdb.MGet(ctx, keys...).Result()
	if err != nil {
		return nil, fmt.Errorf("get presence statuses: %w", err)
	}

	for i, userID := range userIDs {
		value, ok := values[i].(string)
		statuses[userID] = ok && value == "true"
	}

	return statuses, nil
}
