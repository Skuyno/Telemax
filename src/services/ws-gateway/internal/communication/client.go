package communication

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const defaultRequestTimeout = 2 * time.Second

type chatPeersResponse struct {
	UserIDs []string `json:"user_ids"`
}

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func New(baseURL string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: defaultRequestTimeout,
		},
	}
}

func (c *Client) GetChatPeerIDs(
	ctx context.Context,
	userID string,
) ([]string, error) {
	endpoint := fmt.Sprintf(
		"%s/internal/users/%s/chat-peers",
		c.baseURL,
		url.PathEscape(userID),
	)

	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		endpoint,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("create chat peers request: %w", err)
	}

	response, err := c.httpClient.Do(request)
	if err != nil {
		return nil, fmt.Errorf("request chat peers: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf(
			"request chat peers returned status %d",
			response.StatusCode,
		)
	}

	var payload chatPeersResponse
	if err := json.NewDecoder(response.Body).Decode(&payload); err != nil {
		return nil, fmt.Errorf("decode chat peers response: %w", err)
	}

	return payload.UserIDs, nil
}
