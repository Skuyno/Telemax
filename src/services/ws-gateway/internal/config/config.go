package config

import (
	"os"
)

type Config struct {
	JwtSecret string
	NatsUrl   string
	Redis     string
	Port      string
}

func New() *Config {
	return &Config{
		JwtSecret: mustGetEnv("JWT_SECRET"),
		NatsUrl:   getEnv("NATS_URL", "nats://nats:4222"),
		Redis:     getEnv("REDIS_URL", "redis:6379"),
		Port:      getEnv("PORT", "8080"),
	}
}

func getEnv(key string, defaultVal string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return defaultVal
}

func mustGetEnv(key string) string {
	if value, ok := os.LookupEnv(key); ok && value != "" {
		return value
	}
	panic("FATAL: Environment variable " + key + " is strictly required!")
}
